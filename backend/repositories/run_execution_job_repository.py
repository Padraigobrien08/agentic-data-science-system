"""Persistence for :class:`~backend.models.run_execution_job.RunExecutionJob`."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob


class RunExecutionJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: RunExecutionJob) -> None:
        self._session.add(row)

    def get(self, job_id: UUID) -> RunExecutionJob | None:
        return self._session.get(RunExecutionJob, job_id)

    def flush(self) -> None:
        self._session.flush()

    def has_pending_for_run(self, analysis_run_id: UUID) -> bool:
        stmt = (
            select(RunExecutionJob.id)
            .where(
                RunExecutionJob.analysis_run_id == analysis_run_id,
                RunExecutionJob.status == RunExecutionJobStatus.pending,
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None

    def has_open_job_for_run(self, analysis_run_id: UUID) -> bool:
        """True if a job is ``pending`` or ``running`` (blocks another enqueue/retry)."""
        stmt = (
            select(RunExecutionJob.id)
            .where(
                RunExecutionJob.analysis_run_id == analysis_run_id,
                RunExecutionJob.status.in_(
                    (RunExecutionJobStatus.pending, RunExecutionJobStatus.running),
                ),
            )
            .limit(1)
        )
        return self._session.scalar(stmt) is not None

    def cancel_open_jobs_for_run(
        self,
        analysis_run_id: UUID,
        *,
        reason: str = "Cancelled by user",
    ) -> int:
        """Mark ``pending`` / ``running`` jobs cancelled. Returns row count."""
        res = self._session.execute(
            update(RunExecutionJob)
            .where(
                RunExecutionJob.analysis_run_id == analysis_run_id,
                RunExecutionJob.status.in_(
                    (RunExecutionJobStatus.pending, RunExecutionJobStatus.running),
                ),
            )
            .values(
                status=RunExecutionJobStatus.cancelled,
                error_detail=reason,
            )
        )
        return int(res.rowcount or 0)

    def get_latest_for_run(self, analysis_run_id: UUID) -> RunExecutionJob | None:
        stmt = (
            select(RunExecutionJob)
            .where(RunExecutionJob.analysis_run_id == analysis_run_id)
            .order_by(RunExecutionJob.created_at.desc())
            .limit(1)
        )
        return self._session.scalars(stmt).first()

    def claim_next_runnable(self) -> RunExecutionJob | None:
        """
        Claim one pending job whose analysis run is still ``queued``.

        Sets job status to ``running`` and ``claimed_at``. Intended for a **single worker**
        process against SQLite; use row locking / ``SKIP LOCKED`` when moving to Postgres.

        Does not change the run row; the pipeline service transitions ``queued`` → ``running``.
        """
        stmt = (
            select(RunExecutionJob)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.pending,
                AnalysisRun.status == AnalysisRunStatus.queued,
            )
            .order_by(RunExecutionJob.created_at.asc())
            .limit(1)
        )
        job = self._session.scalars(stmt).first()
        if job is None:
            return None
        run = self._session.get(AnalysisRun, job.analysis_run_id)
        if run is None or run.status != AnalysisRunStatus.queued:
            job.status = RunExecutionJobStatus.failed
            job.error_detail = "Run is not queued (state changed before claim)"
            return None
        job.status = RunExecutionJobStatus.running
        job.claimed_at = datetime.now(timezone.utc)
        self._session.flush()
        return job
