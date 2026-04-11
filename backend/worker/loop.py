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
from backend.observability.metrics import monotonic_s, observe_worker_job
from backend.observability.tracing import attach_trace_carrier, bind_current_trace_for_logs, get_tracer
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService
from backend.services.exceptions import RunCancelledDuringExecution
from backend.worker.failure_classification import is_transient_pipeline_failure

logger = logging.getLogger(__name__)
log = structlog.get_logger(__name__)


def _finalize_job_after_attempt(
    session: Session,
    *,
    job_id: UUID,
    analysis_run_id: UUID,
    exc: BaseException | None,
    max_attempts: int,
) -> None:
    job = session.get(RunExecutionJob, job_id)
    if job is None:
        log.warning("worker_job_finalize_missing_row", worker_job_id=str(job_id))
        return
    run = session.get(AnalysisRun, analysis_run_id)
    run_svc = AnalysisRunService(session)

    if exc is not None and run is not None:
        session.refresh(run)

    if exc is None:
        job.status = RunExecutionJobStatus.completed
        job.lease_expires_at = None
        session.commit()
        log.info(
            "worker_job_finalized",
            worker_job_id=str(job_id),
            analysis_run_id=str(analysis_run_id),
            transition="completed_success",
            attempt_count=job.attempt_count,
        )
        return

    if isinstance(exc, RunCancelledDuringExecution):
        job.status = RunExecutionJobStatus.cancelled
        job.lease_expires_at = None
        detail = str(exc)[:2048]
        if job.error_detail is None or not job.error_detail.strip():
            job.error_detail = detail
        session.commit()
        log.info(
            "worker_job_finalized",
            worker_job_id=str(job_id),
            analysis_run_id=str(analysis_run_id),
            transition="cancelled_during_execution",
            attempt_count=job.attempt_count,
        )
        return

    if run is not None and run.status == AnalysisRunStatus.cancelled:
        job.status = RunExecutionJobStatus.cancelled
        job.lease_expires_at = None
        job.error_detail = (job.error_detail or str(exc) or "Cancelled")[:2048]
        session.commit()
        log.info(
            "worker_job_finalized",
            worker_job_id=str(job_id),
            analysis_run_id=str(analysis_run_id),
            transition="cancelled",
            attempt_count=job.attempt_count,
        )
        return

    if run is not None and run.status == AnalysisRunStatus.queued:
        job.status = RunExecutionJobStatus.failed
        job.lease_expires_at = None
        job.error_detail = str(exc)[:2048]
        run_svc.set_error_summary(analysis_run_id, str(exc)[:2048])
        run_svc.transition_status(analysis_run_id, AnalysisRunStatus.error)
        session.commit()
        log.info(
            "worker_job_finalized",
            worker_job_id=str(job_id),
            analysis_run_id=str(analysis_run_id),
            transition="failed_run_still_queued",
            attempt_count=job.attempt_count,
            exc_type=type(exc).__name__,
        )
        return

    transient = is_transient_pipeline_failure(exc)
    if transient and job.attempt_count < max_attempts:
        try:
            run_svc.transition_status(analysis_run_id, AnalysisRunStatus.queued)
            run_svc.set_error_summary(analysis_run_id, None)
        except Exception:
            log.exception(
                "worker_job_requeue_transition_failed",
                worker_job_id=str(job_id),
                analysis_run_id=str(analysis_run_id),
            )
            job.status = RunExecutionJobStatus.failed
            job.lease_expires_at = None
            job.error_detail = str(exc)[:2048]
            session.commit()
            return
        job.status = RunExecutionJobStatus.pending
        job.claimed_at = None
        job.lease_expires_at = None
        job.error_detail = str(exc)[:2048]
        session.commit()
        log.info(
            "worker_job_requeued_transient",
            worker_job_id=str(job_id),
            analysis_run_id=str(analysis_run_id),
            attempt_count=job.attempt_count,
            max_attempts=max_attempts,
            exc_type=type(exc).__name__,
        )
        return

    job.status = RunExecutionJobStatus.failed
    job.lease_expires_at = None
    if job.error_detail is None:
        job.error_detail = str(exc)[:2048]
    session.commit()
    log.info(
        "worker_job_finalized",
        worker_job_id=str(job_id),
        analysis_run_id=str(analysis_run_id),
        transition="failed_terminal_or_exhausted",
        attempt_count=job.attempt_count,
        max_attempts=max_attempts,
        transient=transient,
        exc_type=type(exc).__name__,
        run_status=run.status.value if run is not None else None,
    )


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
    overrides: dict[str, Any] = {}
    trace_carrier: dict[str, str] | None = None

    session = session_factory()
    try:
        repo = RunExecutionJobRepository(session)
        job = repo.claim_next_runnable(lease_seconds=lease_s, max_attempts=max_att)
        if job is None:
            return False
        job_id = job.id
        analysis_run_id = job.analysis_run_id
        raw = job.overrides_json
        if isinstance(raw, dict):
            overrides = dict(raw)
        raw_trace = job.trace_context_json
        if isinstance(raw_trace, dict):
            trace_carrier = {str(k): str(v) for k, v in raw_trace.items() if v is not None}
        session.commit()
    finally:
        session.close()

    assert job_id is not None and analysis_run_id is not None
    log.info(
        "worker_job_claimed",
        worker_job_id=str(job_id),
        analysis_run_id=str(analysis_run_id),
        lease_seconds=lease_s,
        max_attempts=max_att,
    )
    worker_tracer = get_tracer("backend.worker")
    with attach_trace_carrier(trace_carrier):
        with worker_tracer.start_as_current_span(
            "worker.job.execute",
            attributes={
                "worker.job.id": str(job_id),
                "analysis.run.id": str(analysis_run_id),
            },
        ):
            bind_current_trace_for_logs()
            bind_run_context(
                worker_job_id=job_id,
                analysis_run_id=analysis_run_id,
                component="worker",
            )
            t_exec = monotonic_s()
            exc: BaseException | None = None
            try:
                run_session = session_factory()
                try:
                    pipeline = EdgarPipelineExecutionService(run_session)
                    pipeline.execute_analysis_run(
                        analysis_run_id,
                        from_worker=True,
                        tickers=overrides.get("tickers"),
                        analysis_goal=overrides.get("analysis_goal"),
                        refresh=overrides.get("refresh"),
                    )
                finally:
                    run_session.close()
            except BaseException as err:
                exc = err
                observe_worker_job("failed")
                log.exception(
                    "worker_pipeline_failed",
                    worker_job_id=str(job_id),
                    analysis_run_id=str(analysis_run_id),
                )
            else:
                observe_worker_job("completed")
                log.info(
                    "worker_pipeline_ok",
                    worker_job_id=str(job_id),
                    analysis_run_id=str(analysis_run_id),
                    duration_s=round(monotonic_s() - t_exec, 4),
                )
            finally:
                clear_run_context()

    fin = session_factory()
    try:
        _finalize_job_after_attempt(
            fin,
            job_id=job_id,
            analysis_run_id=analysis_run_id,
            exc=exc,
            max_attempts=max_att,
        )
    finally:
        fin.close()
    return True


def run_forever(
    session_factory: Callable[[], Session],
    *,
    poll_interval_s: float = 2.0,
) -> None:
    """Block, processing jobs until interrupted."""
    while True:
        try:
            did_work = process_next_job(session_factory)
        except Exception:
            observe_worker_job("loop_error")
            log.exception("worker_loop_error")
            did_work = False
        if not did_work:
            time.sleep(poll_interval_s)
