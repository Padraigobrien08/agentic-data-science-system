"""Poll the DB job queue and run :class:`~backend.services.edgar_pipeline_execution_service.EdgarPipelineExecutionService`."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.edgar_pipeline_execution_service import EdgarPipelineExecutionService

logger = logging.getLogger(__name__)


def _finalize_job_after_attempt(
    session: Session,
    *,
    job_id: UUID,
    analysis_run_id: UUID,
    exc: BaseException | None,
) -> None:
    job = session.get(RunExecutionJob, job_id)
    if job is None:
        return
    run = session.get(AnalysisRun, analysis_run_id)
    if exc is None:
        job.status = RunExecutionJobStatus.completed
        session.commit()
        return
    if run is not None and run.status == AnalysisRunStatus.cancelled:
        job.status = RunExecutionJobStatus.cancelled
        job.error_detail = (job.error_detail or "Cancelled")[:2048]
        session.commit()
        return
    if run is not None and run.status == AnalysisRunStatus.queued:
        job.status = RunExecutionJobStatus.failed
        job.error_detail = str(exc)[:2048]
        run_svc = AnalysisRunService(session)
        run_svc.set_error_summary(analysis_run_id, str(exc)[:2048])
        run_svc.transition_status(analysis_run_id, AnalysisRunStatus.error)
        session.commit()
        return
    job.status = RunExecutionJobStatus.completed
    session.commit()


def process_next_job(session_factory: Callable[[], Session]) -> bool:
    """
    Claim at most one pending job, execute the pipeline in a fresh session, finalize job status.

    Returns True if a job was claimed (whether or not execution raised after persistence).
    """
    job_id: UUID | None = None
    analysis_run_id: UUID | None = None
    overrides: dict[str, Any] = {}

    session = session_factory()
    try:
        repo = RunExecutionJobRepository(session)
        job = repo.claim_next_runnable()
        if job is None:
            return False
        job_id = job.id
        analysis_run_id = job.analysis_run_id
        raw = job.overrides_json
        if isinstance(raw, dict):
            overrides = dict(raw)
        session.commit()
    finally:
        session.close()

    assert job_id is not None and analysis_run_id is not None
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
        logger.exception("Pipeline execution failed for run %s job %s", analysis_run_id, job_id)

    fin = session_factory()
    try:
        _finalize_job_after_attempt(
            fin,
            job_id=job_id,
            analysis_run_id=analysis_run_id,
            exc=exc,
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
            logger.exception("Worker loop error")
            did_work = False
        if not did_work:
            time.sleep(poll_interval_s)
