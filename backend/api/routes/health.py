"""Liveness and dependency checks."""

from datetime import datetime, timezone

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from backend import __version__
from backend.api.deps import DbSession
from backend.config.settings import get_settings
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.schemas.health import DatabaseHealth, HealthResponse, WorkerHealthResponse

router = APIRouter()


@router.get("/ready")
def readiness(db: DbSession) -> JSONResponse:
    """
    Readiness for orchestrators: ``200`` when the database accepts connections, else ``503``.
    """
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready", "detail": str(exc)},
        )
    return JSONResponse(status_code=status.HTTP_200_OK, content={"status": "ready"})


@router.get("/health", response_model=HealthResponse)
def health(db: DbSession) -> HealthResponse:
    """Verify process is up and database accepts connections."""
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
        detail = None
    except Exception as exc:  # noqa: BLE001 — intentional boundary for health reporting
        db_ok = False
        detail = str(exc)
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=__version__,
        database=DatabaseHealth(ok=db_ok, detail=detail),
    )


@router.get("/worker/health", response_model=WorkerHealthResponse)
def worker_health(db: DbSession) -> WorkerHealthResponse:
    """
    DB-backed worker queue view (no worker process coupling).

    Use with smoke tests or alerts: e.g. ``stale_running_jobs`` or backlog with no active lease
    for a prolonged period suggests the worker is not making progress.
    """
    settings = get_settings()
    repo = RunExecutionJobRepository(db)
    try:
        snap = repo.queue_observability_snapshot(max_attempts=settings.run_job_max_attempts)
        last_at = repo.last_terminal_job_activity_at()
    except SQLAlchemyError:
        return WorkerHealthResponse(
            queue_depth=0,
            jobs_running_lease_ok=0,
            jobs_running_stale_lease=0,
            open_jobs_on_cancelled_run=0,
            last_terminal_job_at=None,
            age_seconds_since_last_terminal_job=None,
            stale_running_jobs=False,
            backlog_without_active_lease=False,
        )
    age: float | None = None
    if last_at is not None:
        la = last_at if last_at.tzinfo is not None else last_at.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - la).total_seconds()
    return WorkerHealthResponse(
        queue_depth=snap.pending_claimable,
        jobs_running_lease_ok=snap.jobs_running_lease_ok,
        jobs_running_stale_lease=snap.jobs_running_stale_lease,
        open_jobs_on_cancelled_run=snap.open_jobs_on_cancelled_run,
        last_terminal_job_at=last_at,
        age_seconds_since_last_terminal_job=age,
        stale_running_jobs=snap.jobs_running_stale_lease > 0,
        backlog_without_active_lease=snap.pending_claimable > 0 and snap.jobs_running_lease_ok == 0,
    )
