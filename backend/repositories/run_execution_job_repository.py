"""Persistence for :class:`~backend.models.run_execution_job.RunExecutionJob`."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.services.analysis_run_service import AnalysisRunService


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
                lease_expires_at=None,
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

    def _for_update(self, stmt, *, dialect_name: str):
        if dialect_name == "postgresql":
            return stmt.with_for_update(skip_locked=True)
        return stmt.with_for_update()

    def claim_next_runnable(
        self,
        *,
        lease_seconds: float,
        max_attempts: int,
    ) -> RunExecutionJob | None:
        """
        Atomically claim one runnable job:

        1. **Stale lease, run still queued** — extend lease (same attempt_count).
        2. **Stale lease, run running** — fail or requeue: if attempts exhausted mark failed;
           else bump attempt_count, reset job to pending and run error→queued (idempotent reclaim).
        3. **Fresh pending** — run queued, attempt_count < max_attempts: set running, lease,
           increment attempt_count.

        PostgreSQL uses ``FOR UPDATE SKIP LOCKED``. SQLite uses ``FOR UPDATE`` (single-writer friendly).
        """
        now = datetime.now(timezone.utc)
        lease_end = now + timedelta(seconds=lease_seconds)
        dialect_name = self._session.get_bind().dialect.name
        run_svc = AnalysisRunService(self._session)

        # --- 0) Run cancelled but job still open (zombie cleanup; auditable) ---
        q_orphan = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status.in_(
                    (RunExecutionJobStatus.pending, RunExecutionJobStatus.running),
                ),
                AnalysisRun.status == AnalysisRunStatus.cancelled,
            )
            .order_by(RunExecutionJob.created_at.asc())
            .limit(1),
            dialect_name=dialect_name,
        )
        jid = self._session.scalar(q_orphan)
        if jid is not None:
            job = self._session.get(RunExecutionJob, jid)
            if job is not None:
                job.status = RunExecutionJobStatus.cancelled
                job.error_detail = (job.error_detail or "Run was cancelled; cleaning up open job")[:2048]
                job.lease_expires_at = None
                self._session.flush()
            return None

        # --- 1) Stale: worker died before pipeline moved run off queued ---
        q_stale_queued = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.running,
                RunExecutionJob.lease_expires_at.is_not(None),
                RunExecutionJob.lease_expires_at < now,
                AnalysisRun.status == AnalysisRunStatus.queued,
            )
            .order_by(RunExecutionJob.claimed_at.asc().nulls_first())
            .limit(1),
            dialect_name=dialect_name,
        )
        jid = self._session.scalar(q_stale_queued)
        if jid is not None:
            job = self._session.get(RunExecutionJob, jid)
            run = self._session.get(AnalysisRun, job.analysis_run_id) if job else None
            if job is not None and run is not None and run.status == AnalysisRunStatus.queued:
                job.claimed_at = now
                job.lease_expires_at = lease_end
                self._session.flush()
                return job

        # --- 2) Stale: pipeline had committed run=running, worker died ---
        q_stale_running = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.running,
                RunExecutionJob.lease_expires_at.is_not(None),
                RunExecutionJob.lease_expires_at < now,
                AnalysisRun.status == AnalysisRunStatus.running,
            )
            .order_by(RunExecutionJob.claimed_at.asc().nulls_first())
            .limit(1),
            dialect_name=dialect_name,
        )
        jid = self._session.scalar(q_stale_running)
        if jid is not None:
            job = self._session.get(RunExecutionJob, jid)
            run = self._session.get(AnalysisRun, job.analysis_run_id) if job else None
            if job is not None and run is not None and run.status == AnalysisRunStatus.running:
                if job.attempt_count >= max_attempts:
                    detail = "Lease expired and max execution attempts exhausted"
                    job.status = RunExecutionJobStatus.failed
                    job.error_detail = detail[:2048]
                    job.lease_expires_at = None
                    run_svc.set_error_summary(run.id, detail[:2048])
                    run_svc.transition_status(run.id, AnalysisRunStatus.error)
                    self._session.flush()
                    return None
                run_svc.set_error_summary(run.id, "Worker lease expired; rescheduling")
                run_svc.transition_status(run.id, AnalysisRunStatus.error)
                run_svc.transition_status(run.id, AnalysisRunStatus.queued)
                run_svc.set_error_summary(run.id, None)
                job.status = RunExecutionJobStatus.pending
                job.claimed_at = None
                job.lease_expires_at = None
                job.error_detail = "lease_expired_mid_run"
                self._session.flush()
                return None

        # --- 3) Fresh pending row ---
        q_pending = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.pending,
                AnalysisRun.status == AnalysisRunStatus.queued,
                RunExecutionJob.attempt_count < max_attempts,
            )
            .order_by(RunExecutionJob.created_at.asc())
            .limit(1),
            dialect_name=dialect_name,
        )
        jid = self._session.scalar(q_pending)
        if jid is None:
            return None
        job = self._session.get(RunExecutionJob, jid)
        if job is None:
            return None
        run = self._session.get(AnalysisRun, job.analysis_run_id)
        if run is None or run.status != AnalysisRunStatus.queued:
            if run is not None and run.status == AnalysisRunStatus.cancelled:
                job.status = RunExecutionJobStatus.cancelled
                job.error_detail = (job.error_detail or "Run was cancelled before claim")[:2048]
            else:
                job.status = RunExecutionJobStatus.failed
                job.error_detail = "Run is not queued (state changed before claim)"
            job.lease_expires_at = None
            self._session.flush()
            return None
        job.status = RunExecutionJobStatus.running
        job.claimed_at = now
        job.lease_expires_at = lease_end
        job.attempt_count += 1
        self._session.flush()
        return job
