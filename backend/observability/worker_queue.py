"""Shared DB-backed worker queue observability contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.repositories.run_execution_job_repository import (
    RunExecutionJobRepository,
    WorkerQueueSnapshot,
)


@dataclass(frozen=True, slots=True)
class WorkerQueueObservabilityResult:
    """Worker queue observability result shared by JSON and Prometheus surfaces."""

    database_ok: bool
    database_detail: str | None
    queue_state_known: bool
    snapshot: WorkerQueueSnapshot | None
    last_terminal_job_at: datetime | None
    age_seconds_since_last_terminal_job: float | None
    stale_running_jobs: bool | None
    backlog_without_active_lease: bool | None


def get_worker_queue_observability(
    session: Session,
    *,
    max_attempts: int,
) -> WorkerQueueObservabilityResult:
    """Read queue observability from the database without masking failures as empty state."""
    repo = RunExecutionJobRepository(session)
    try:
        snapshot = repo.queue_observability_snapshot(max_attempts=max_attempts)
        last_terminal_job_at = repo.last_terminal_job_activity_at()
    except SQLAlchemyError as exc:
        return WorkerQueueObservabilityResult(
            database_ok=False,
            database_detail=str(exc),
            queue_state_known=False,
            snapshot=None,
            last_terminal_job_at=None,
            age_seconds_since_last_terminal_job=None,
            stale_running_jobs=None,
            backlog_without_active_lease=None,
        )

    normalized_last_terminal_job_at = None
    age_seconds_since_last_terminal_job = None
    if last_terminal_job_at is not None:
        normalized_last_terminal_job_at = last_terminal_job_at
        if normalized_last_terminal_job_at.tzinfo is None:
            normalized_last_terminal_job_at = normalized_last_terminal_job_at.replace(
                tzinfo=timezone.utc,
            )
        age_seconds_since_last_terminal_job = (
            datetime.now(timezone.utc) - normalized_last_terminal_job_at
        ).total_seconds()

    return WorkerQueueObservabilityResult(
        database_ok=True,
        database_detail=None,
        queue_state_known=True,
        snapshot=snapshot,
        last_terminal_job_at=normalized_last_terminal_job_at,
        age_seconds_since_last_terminal_job=age_seconds_since_last_terminal_job,
        stale_running_jobs=snapshot.jobs_running_stale_lease > 0,
        backlog_without_active_lease=(
            snapshot.pending_claimable > 0 and snapshot.jobs_running_lease_ok == 0
        ),
    )
