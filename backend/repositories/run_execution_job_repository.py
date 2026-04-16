"""Persistence for :class:`~backend.models.run_execution_job.RunExecutionJob`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.exceptions import WorkerLeaseLostError


@dataclass(frozen=True, slots=True)
class WorkerQueueSnapshot:
    """Point-in-time counts for worker queue observability (aligned with claim logic)."""

    pending_claimable: int
    jobs_running_lease_ok: int
    jobs_running_stale_lease: int
    open_jobs_on_cancelled_run: int


class RunExecutionJobRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: RunExecutionJob) -> None:
        self._session.add(row)

    def get(self, job_id: UUID) -> RunExecutionJob | None:
        return self._session.get(RunExecutionJob, job_id)

    def flush(self) -> None:
        self._session.flush()

    def _new_claim_token(self) -> str:
        return str(uuid4())

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
                claim_token=None,
                lease_expires_at=None,
            )
        )
        return int(res.rowcount or 0)

    def get_latest_for_run(self, analysis_run_id: UUID) -> RunExecutionJob | None:
        rows = self.list_for_run(analysis_run_id, limit=1)
        return rows[0] if rows else None

    def list_for_run(self, analysis_run_id: UUID, *, limit: int | None = None) -> list[RunExecutionJob]:
        stmt = (
            select(RunExecutionJob)
            .where(RunExecutionJob.analysis_run_id == analysis_run_id)
            .order_by(RunExecutionJob.attempt_count.desc(), RunExecutionJob.created_at.desc())
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self._session.scalars(stmt).all())

    def create_pending_attempt(
        self,
        *,
        analysis_run_id: UUID,
        attempt_count: int,
        overrides_json: dict | list | None,
        trace_context_json: dict | list | None,
    ) -> RunExecutionJob:
        row = RunExecutionJob(
            analysis_run_id=analysis_run_id,
            status=RunExecutionJobStatus.pending,
            overrides_json=overrides_json,
            trace_context_json=trace_context_json,
            attempt_count=attempt_count,
            claimed_at=None,
            claim_token=None,
            lease_expires_at=None,
            error_detail=None,
        )
        self.add(row)
        self.flush()
        return row

    def queue_observability_snapshot(self, *, max_attempts: int) -> WorkerQueueSnapshot:
        """
        DB-backed queue picture for metrics (no worker process required).

        * **pending_claimable** — matches fresh-claim branch: pending, run queued, attempts left.
        * **jobs_running_lease_ok** — running with a non-expired lease.
        * **jobs_running_stale_lease** — running with missing or expired lease (reclaim candidates).
        * **open_jobs_on_cancelled_run** — pending/running while run is cancelled (zombie cleanup backlog).
        """
        now = datetime.now(timezone.utc)
        sess = self._session

        pending_claimable = int(
            sess.scalar(
                select(func.count())
                .select_from(RunExecutionJob)
                .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
                .where(
                    RunExecutionJob.status == RunExecutionJobStatus.pending,
                    AnalysisRun.status == AnalysisRunStatus.queued,
                    RunExecutionJob.attempt_count <= max_attempts,
                )
            )
            or 0
        )

        jobs_running_lease_ok = int(
            sess.scalar(
                select(func.count())
                .select_from(RunExecutionJob)
                .where(
                    RunExecutionJob.status == RunExecutionJobStatus.running,
                    RunExecutionJob.lease_expires_at.is_not(None),
                    RunExecutionJob.lease_expires_at >= now,
                )
            )
            or 0
        )

        jobs_running_stale_lease = int(
            sess.scalar(
                select(func.count())
                .select_from(RunExecutionJob)
                .where(
                    RunExecutionJob.status == RunExecutionJobStatus.running,
                    or_(
                        RunExecutionJob.lease_expires_at.is_(None),
                        RunExecutionJob.lease_expires_at < now,
                    ),
                )
            )
            or 0
        )

        open_jobs_on_cancelled_run = int(
            sess.scalar(
                select(func.count())
                .select_from(RunExecutionJob)
                .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
                .where(
                    RunExecutionJob.status.in_(
                        (RunExecutionJobStatus.pending, RunExecutionJobStatus.running),
                    ),
                    AnalysisRun.status == AnalysisRunStatus.cancelled,
                )
            )
            or 0
        )

        return WorkerQueueSnapshot(
            pending_claimable=pending_claimable,
            jobs_running_lease_ok=jobs_running_lease_ok,
            jobs_running_stale_lease=jobs_running_stale_lease,
            open_jobs_on_cancelled_run=open_jobs_on_cancelled_run,
        )

    def last_terminal_job_activity_at(self) -> datetime | None:
        """Latest ``updated_at`` among terminal execution jobs (DB-visible worker progress)."""
        return self._session.scalar(
            select(func.max(RunExecutionJob.updated_at)).where(
                RunExecutionJob.status.in_(
                    (
                        RunExecutionJobStatus.completed,
                        RunExecutionJobStatus.failed,
                        RunExecutionJobStatus.cancelled,
                    ),
                ),
            ),
        )

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

        1. **Stale or missing lease, run still queued** — extend lease (same attempt_count).
        2. **Stale or missing lease, run running** — fail the stale attempt and create the next
           pending attempt row when tries remain.
        3. **Fresh pending** — run queued, attempt_count <= max_attempts: set running, lease,
           preserve the attempt number on that row.

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
                job.claim_token = None
                job.lease_expires_at = None
                self._session.flush()
            return None

        # --- 1) Stale / no lease: worker died before pipeline moved run off queued ---
        q_stale_queued = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.running,
                or_(
                    RunExecutionJob.lease_expires_at.is_(None),
                    RunExecutionJob.lease_expires_at < now,
                ),
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
                job.claim_token = self._new_claim_token()
                job.lease_expires_at = lease_end
                self._session.flush()
                return job

        # --- 2) Stale / no lease: pipeline had committed run=running, worker died ---
        q_stale_running = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.running,
                or_(
                    RunExecutionJob.lease_expires_at.is_(None),
                    RunExecutionJob.lease_expires_at < now,
                ),
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
                    job.claim_token = None
                    job.lease_expires_at = None
                    run_svc.set_error_summary(run.id, detail[:2048])
                    run_svc.transition_status(run.id, AnalysisRunStatus.error)
                    self._session.flush()
                    return None
                run_svc.set_error_summary(run.id, "Worker lease expired; rescheduling")
                run_svc.transition_status(run.id, AnalysisRunStatus.error)
                run_svc.transition_status(run.id, AnalysisRunStatus.queued)
                run_svc.set_error_summary(run.id, None)
                job.status = RunExecutionJobStatus.failed
                job.claim_token = None
                job.lease_expires_at = None
                job.error_detail = "lease_expired_mid_run"
                self.create_pending_attempt(
                    analysis_run_id=job.analysis_run_id,
                    attempt_count=job.attempt_count + 1,
                    overrides_json=job.overrides_json,
                    trace_context_json=job.trace_context_json,
                )
                self._session.flush()
                return None

        # --- 3) Fresh pending row ---
        q_pending = self._for_update(
            select(RunExecutionJob.id)
            .join(AnalysisRun, RunExecutionJob.analysis_run_id == AnalysisRun.id)
            .where(
                RunExecutionJob.status == RunExecutionJobStatus.pending,
                AnalysisRun.status == AnalysisRunStatus.queued,
                RunExecutionJob.attempt_count <= max_attempts,
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
            job.claim_token = None
            job.lease_expires_at = None
            self._session.flush()
            return None
        job.status = RunExecutionJobStatus.running
        job.claimed_at = now
        job.claim_token = self._new_claim_token()
        job.lease_expires_at = lease_end
        self._session.flush()
        return job

    def renew_lease(
        self,
        job_id: UUID,
        claim_token: str,
        *,
        lease_seconds: float,
    ) -> datetime:
        lease_end = datetime.now(timezone.utc) + timedelta(seconds=lease_seconds)
        res = self._session.execute(
            update(RunExecutionJob)
            .where(
                RunExecutionJob.id == job_id,
                RunExecutionJob.status == RunExecutionJobStatus.running,
                RunExecutionJob.claim_token == claim_token,
            )
            .values(lease_expires_at=lease_end)
        )
        if int(res.rowcount or 0) != 1:
            raise WorkerLeaseLostError("Worker no longer owns the claimed execution job")
        return lease_end

    def finalize_attempt_if_owned(
        self,
        job_id: UUID,
        claim_token: str,
        *,
        status: RunExecutionJobStatus,
        error_detail: str | None = None,
    ) -> bool:
        values: dict[str, object] = {
            "status": status,
            "claim_token": None,
            "lease_expires_at": None,
        }
        if error_detail is not None:
            values["error_detail"] = error_detail[:2048]
        res = self._session.execute(
            update(RunExecutionJob)
            .where(
                RunExecutionJob.id == job_id,
                RunExecutionJob.status == RunExecutionJobStatus.running,
                RunExecutionJob.claim_token == claim_token,
            )
            .values(**values)
        )
        return int(res.rowcount or 0) == 1

    def requeue_if_owned(
        self,
        job_id: UUID,
        claim_token: str,
        *,
        error_detail: str | None = None,
    ) -> bool:
        values: dict[str, object] = {
            "status": RunExecutionJobStatus.pending,
            "claimed_at": None,
            "claim_token": None,
            "lease_expires_at": None,
        }
        if error_detail is not None:
            values["error_detail"] = error_detail[:2048]
        res = self._session.execute(
            update(RunExecutionJob)
            .where(
                RunExecutionJob.id == job_id,
                RunExecutionJob.status == RunExecutionJobStatus.running,
                RunExecutionJob.claim_token == claim_token,
            )
            .values(**values)
        )
        return int(res.rowcount or 0) == 1
