"""Poll the DB job queue and run :class:`~backend.services.edgar_pipeline_execution_service.EdgarPipelineExecutionService`."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

import structlog
from sqlalchemy.orm import Session

from backend.config.settings import get_settings
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob

from backend.observability.context import bind_run_context, clear_run_context
from backend.observability.metrics import (
    mark_worker_loop_tick,
    monotonic_s,
    observe_worker_attempt_complete,
    observe_worker_job,
    observe_worker_job_claimed,
)
from backend.observability.tracing import attach_trace_carrier, bind_current_trace_for_logs, get_tracer
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.agentic_investigation_execution_service import (
    AgenticInvestigationExecutionService,
    ENGINE_AGENTIC,
    select_run_engine,
)
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService
from backend.services.exceptions import RunCancelledDuringExecution, WorkerLeaseLostError
from backend.worker.lease import WorkerLeaseGuard
from backend.worker.failure_classification import is_transient_pipeline_failure

logger = logging.getLogger(__name__)
log = structlog.get_logger(__name__)


def _worker_log_fields(
    *,
    job_id: UUID,
    analysis_run_id: UUID,
    run: AnalysisRun | None = None,
    orchestration_run_id: str | None = None,
) -> dict[str, Any]:
    """Stable ids for worker structured logs (``run_id`` is the analysis run UUID)."""
    rid = str(analysis_run_id)
    fields: dict[str, Any] = {
        "run_id": rid,
        "analysis_run_id": rid,
        "worker_job_id": str(job_id),
    }
    orch = orchestration_run_id
    if orch is None and run is not None and run.correlation_id:
        orch = run.correlation_id
    if orch:
        fields["orchestration_run_id"] = orch
    return fields


def _coarse_worker_outcome(finalize_outcome: str) -> str:
    if finalize_outcome == "completed_success":
        return "completed"
    if finalize_outcome == "requeued_transient":
        return "requeued"
    if finalize_outcome in ("cancelled_during_execution", "cancelled"):
        return "cancelled"
    return "failed"


def _finalize_job_after_attempt(
    session: Session,
    *,
    job_id: UUID,
    analysis_run_id: UUID,
    claim_token: str,
    exc: BaseException | None,
    max_attempts: int,
    t_wall_start: float,
) -> str | None:
    job = session.get(RunExecutionJob, job_id)
    if job is None:
        log.warning(
            "worker_job_finalize_missing_row",
            worker_event="worker_job_finish",
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id),
        )
        return None
    run = session.get(AnalysisRun, analysis_run_id)
    run_svc = AnalysisRunService(session)
    repo = RunExecutionJobRepository(session)

    if exc is not None and run is not None:
        session.refresh(run)

    if isinstance(exc, WorkerLeaseLostError):
        session.rollback()
        log.info(
            "worker_job_finished",
            worker_event="worker_job_finish",
            transition="lease_lost",
            attempt_count=job.attempt_count,
            wall_duration_s=round(monotonic_s() - t_wall_start, 4),
            exc_type=type(exc).__name__,
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
        )
        return "lease_lost"

    if exc is None:
        if not repo.finalize_attempt_if_owned(
            job_id,
            claim_token,
            status=RunExecutionJobStatus.completed,
        ):
            session.rollback()
            return "lease_lost"
        session.commit()
        log.info(
            "worker_job_finished",
            worker_event="worker_job_finish",
            transition="completed_success",
            attempt_count=job.attempt_count,
            wall_duration_s=round(monotonic_s() - t_wall_start, 4),
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
        )
        return "completed_success"

    if isinstance(exc, RunCancelledDuringExecution):
        detail = str(exc)[:2048]
        if not repo.finalize_attempt_if_owned(
            job_id,
            claim_token,
            status=RunExecutionJobStatus.cancelled,
            error_detail=job.error_detail if job.error_detail and job.error_detail.strip() else detail,
        ):
            session.rollback()
            return "lease_lost"
        session.commit()
        log.info(
            "worker_job_finished",
            worker_event="worker_job_finish",
            transition="cancelled_during_execution",
            attempt_count=job.attempt_count,
            wall_duration_s=round(monotonic_s() - t_wall_start, 4),
            exc_type=type(exc).__name__,
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
        )
        return "cancelled_during_execution"

    if run is not None and run.status == AnalysisRunStatus.cancelled:
        if not repo.finalize_attempt_if_owned(
            job_id,
            claim_token,
            status=RunExecutionJobStatus.cancelled,
            error_detail=(job.error_detail or str(exc) or "Cancelled")[:2048],
        ):
            session.rollback()
            return "lease_lost"
        session.commit()
        log.info(
            "worker_job_finished",
            worker_event="worker_job_finish",
            transition="cancelled",
            attempt_count=job.attempt_count,
            wall_duration_s=round(monotonic_s() - t_wall_start, 4),
            exc_type=type(exc).__name__,
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
        )
        return "cancelled"

    if run is not None and run.status == AnalysisRunStatus.queued:
        if not repo.finalize_attempt_if_owned(
            job_id,
            claim_token,
            status=RunExecutionJobStatus.failed,
            error_detail=str(exc)[:2048],
        ):
            session.rollback()
            return "lease_lost"
        run_svc.set_error_summary(analysis_run_id, str(exc)[:2048])
        run_svc.transition_status(analysis_run_id, AnalysisRunStatus.error)
        session.commit()
        log.warning(
            "worker_job_finished",
            worker_event="worker_job_finish",
            transition="failed_run_still_queued",
            attempt_count=job.attempt_count,
            wall_duration_s=round(monotonic_s() - t_wall_start, 4),
            exc_type=type(exc).__name__,
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
        )
        return "failed_run_still_queued"

    transient = is_transient_pipeline_failure(exc)
    if transient and job.attempt_count < max_attempts:
        next_attempt = job.attempt_count + 1
        overrides_json = job.overrides_json
        trace_context_json = job.trace_context_json
        try:
            if not repo.finalize_attempt_if_owned(
                job_id,
                claim_token,
                status=RunExecutionJobStatus.failed,
                error_detail=str(exc)[:2048],
            ):
                session.rollback()
                return "lease_lost"
            run_svc.transition_status(analysis_run_id, AnalysisRunStatus.queued)
            run_svc.set_error_summary(analysis_run_id, None)
            repo.create_pending_attempt(
                analysis_run_id=analysis_run_id,
                attempt_count=next_attempt,
                overrides_json=overrides_json,
                trace_context_json=trace_context_json,
            )
        except Exception:
            session.rollback()
            log.exception(
                "worker_job_requeue_transition_failed",
                worker_event="worker_job_failure",
                **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
            )
            if not repo.finalize_attempt_if_owned(
                job_id,
                claim_token,
                status=RunExecutionJobStatus.failed,
                error_detail=str(exc)[:2048],
            ):
                session.rollback()
                return "lease_lost"
            session.commit()
            log.error(
                "worker_job_finished",
                worker_event="worker_job_finish",
                transition="requeue_transition_failed",
                wall_duration_s=round(monotonic_s() - t_wall_start, 4),
                exc_type=type(exc).__name__,
                **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
            )
            return "requeue_transition_failed"
        session.commit()
        log.info(
            "worker_job_retry_scheduled",
            worker_event="worker_job_retry",
            attempt_count=job.attempt_count,
            max_attempts=max_attempts,
            exc_type=type(exc).__name__,
            wall_duration_s=round(monotonic_s() - t_wall_start, 4),
            **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
        )
        return "requeued_transient"

    if not repo.finalize_attempt_if_owned(
        job_id,
        claim_token,
        status=RunExecutionJobStatus.failed,
        error_detail=job.error_detail if job.error_detail is not None else str(exc)[:2048],
    ):
        session.rollback()
        return "lease_lost"
    session.commit()
    log.warning(
        "worker_job_finished",
        worker_event="worker_job_finish",
        transition="failed_terminal_or_exhausted",
        attempt_count=job.attempt_count,
        max_attempts=max_attempts,
        transient=transient,
        exc_type=type(exc).__name__,
        run_status=run.status.value if run is not None else None,
        wall_duration_s=round(monotonic_s() - t_wall_start, 4),
        **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id, run=run),
    )
    return "failed_terminal_or_exhausted"


def process_next_job(
    session_factory: Callable[[], Session],
    *,
    lease_seconds: float | None = None,
    max_attempts: int | None = None,
) -> bool:
    """
    Claim at most one pending or stale-leased job, execute the pipeline, finalize job status.

    Returns True if a job was claimed (whether or not execution raised after persistence).
    """
    settings = get_settings()
    lease_s = lease_seconds if lease_seconds is not None else settings.run_job_lease_seconds
    max_att = max_attempts if max_attempts is not None else settings.run_job_max_attempts

    job_id: UUID | None = None
    analysis_run_id: UUID | None = None
    claim_token: str | None = None
    attempt_after_claim: int | None = None
    overrides: dict[str, Any] = {}
    trace_carrier: dict[str, str] | None = None
    lease_guard: WorkerLeaseGuard | None = None

    session = session_factory()
    try:
        repo = RunExecutionJobRepository(session)
        job = repo.claim_next_runnable(lease_seconds=lease_s, max_attempts=max_att)
        if job is None:
            return False
        job_id = job.id
        analysis_run_id = job.analysis_run_id
        claim_token = job.claim_token
        attempt_after_claim = job.attempt_count
        raw = job.overrides_json
        if isinstance(raw, dict):
            overrides = dict(raw)
        raw_trace = job.trace_context_json
        if isinstance(raw_trace, dict):
            trace_carrier = {str(k): str(v) for k, v in raw_trace.items() if v is not None}
        session.commit()
        assert claim_token is not None
        lease_guard = WorkerLeaseGuard(
            session_factory,
            job_id=job_id,
            claim_token=claim_token,
            lease_seconds=lease_s,
        )
        lease_guard.start()
        observe_worker_job_claimed()
    finally:
        session.close()

    assert job_id is not None and analysis_run_id is not None and claim_token is not None
    assert attempt_after_claim is not None

    peek = session_factory()
    orchestration_run_id_at_claim: str | None = None
    try:
        run_row = peek.get(AnalysisRun, analysis_run_id)
        if run_row is not None and run_row.correlation_id:
            orchestration_run_id_at_claim = run_row.correlation_id
    finally:
        peek.close()

    t_wall_start = monotonic_s()
    log.info(
        "worker_job_claimed",
        worker_event="worker_job_claim",
        attempt_count=attempt_after_claim,
        lease_seconds=lease_s,
        max_attempts=max_att,
        **_worker_log_fields(
            job_id=job_id,
            analysis_run_id=analysis_run_id,
            orchestration_run_id=orchestration_run_id_at_claim,
        ),
    )
    worker_tracer = get_tracer("backend.worker")
    with attach_trace_carrier(trace_carrier):
        with worker_tracer.start_as_current_span(
            "worker.job.execute",
            attributes={
                "worker.job.id": str(job_id),
                "analysis.run.id": str(analysis_run_id),
                "run.id": str(analysis_run_id),
            },
        ):
            bind_current_trace_for_logs()
            bind_run_context(
                worker_job_id=job_id,
                analysis_run_id=analysis_run_id,
                orchestration_run_id=orchestration_run_id_at_claim,
                component="worker",
            )
            t_exec = monotonic_s()
            exc: BaseException | None = None
            try:
                log.info(
                    "worker_job_execution_started",
                    worker_event="worker_job_start",
                    attempt_count=attempt_after_claim,
                    **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id),
                )
                run_session = session_factory()
                try:
                    checkpoint = lease_guard.checkpoint if lease_guard is not None else None
                    run_for_engine = run_session.get(AnalysisRun, analysis_run_id)
                    engine = (
                        select_run_engine(run_for_engine, get_settings())
                        if run_for_engine is not None
                        else "edgar"
                    )
                    if engine == ENGINE_AGENTIC:
                        AgenticInvestigationExecutionService(run_session).execute_analysis_run(
                            analysis_run_id,
                            from_worker=True,
                            analysis_goal=overrides.get("analysis_goal"),
                            execution_checkpoint=checkpoint,
                        )
                    else:
                        EdgarPipelineExecutionService(run_session).execute_analysis_run(
                            analysis_run_id,
                            from_worker=True,
                            tickers=overrides.get("tickers"),
                            analysis_goal=overrides.get("analysis_goal"),
                            refresh=overrides.get("refresh"),
                            execution_checkpoint=checkpoint,
                        )
                finally:
                    run_session.close()
            except BaseException as err:
                exc = err
                log.exception(
                    "worker_pipeline_failed",
                    worker_event="worker_job_failure",
                    attempt_count=attempt_after_claim,
                    pipeline_duration_s=round(monotonic_s() - t_exec, 4),
                    wall_duration_s=round(monotonic_s() - t_wall_start, 4),
                    exc_type=type(err).__name__,
                    **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id),
                )
            else:
                log.info(
                    "worker_pipeline_ok",
                    worker_event="worker_job_pipeline_ok",
                    attempt_count=attempt_after_claim,
                    pipeline_duration_s=round(monotonic_s() - t_exec, 4),
                    wall_duration_s=round(monotonic_s() - t_wall_start, 4),
                    **_worker_log_fields(job_id=job_id, analysis_run_id=analysis_run_id),
                )
            finally:
                clear_run_context()

    if lease_guard is not None:
        lease_guard.stop()

    fin = session_factory()
    try:
        finalize_outcome = _finalize_job_after_attempt(
            fin,
            job_id=job_id,
            analysis_run_id=analysis_run_id,
            claim_token=claim_token,
            exc=exc,
            max_attempts=max_att,
            t_wall_start=t_wall_start,
        )
    finally:
        fin.close()

    wall_duration_s = monotonic_s() - t_wall_start
    if finalize_outcome is not None:
        observe_worker_attempt_complete(
            finalize_outcome=finalize_outcome,
            coarse_outcome=_coarse_worker_outcome(finalize_outcome),
            wall_duration_s=wall_duration_s,
        )
    else:
        observe_worker_job("finalize_missing_job")
    return True


def run_forever(
    session_factory: Callable[[], Session],
    *,
    poll_interval_s: float = 2.0,
) -> None:
    """Block, processing jobs until interrupted."""
    while True:
        mark_worker_loop_tick()
        try:
            did_work = process_next_job(session_factory)
        except Exception:
            observe_worker_job("loop_error")
            log.exception("worker_loop_error")
            did_work = False
        if not did_work:
            time.sleep(poll_interval_s)
