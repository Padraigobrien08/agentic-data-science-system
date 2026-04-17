"""Liveness and dependency checks."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend import __version__
from backend.api.auth_deps import OpsTokenDep
from backend.api.deps import DbSession
from backend.config.settings import get_settings
from backend.llm.factory import describe_llm_runtime
from backend.observability.worker_queue import get_worker_queue_observability
from backend.schemas.health import DatabaseHealth, HealthResponse, LlmHealth, WorkerHealthResponse

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
    settings = get_settings()
    lk, lr, lm = describe_llm_runtime(settings)
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=__version__,
        database=DatabaseHealth(ok=db_ok, detail=detail),
        llm=LlmHealth(provider=lk, ready=lr, message=lm),
    )


@router.get("/worker/health", response_model=WorkerHealthResponse)
def worker_health(db: DbSession, _ops_token: OpsTokenDep) -> WorkerHealthResponse:
    """
    DB-backed worker queue view (no worker process coupling).

    Use with smoke tests or alerts: e.g. ``stale_running_jobs`` or backlog with no active lease
    for a prolonged period suggests the worker is not making progress.
    """
    settings = get_settings()
    result = get_worker_queue_observability(
        db,
        max_attempts=settings.run_job_max_attempts,
    )
    return WorkerHealthResponse(
        status="ok" if result.database_ok else "degraded",
        database=DatabaseHealth(
            ok=result.database_ok,
            detail=result.database_detail,
        ),
        queue_state_known=result.queue_state_known,
        queue_depth=(
            result.snapshot.pending_claimable
            if result.snapshot is not None
            else None
        ),
        jobs_running_lease_ok=(
            result.snapshot.jobs_running_lease_ok
            if result.snapshot is not None
            else None
        ),
        jobs_running_stale_lease=(
            result.snapshot.jobs_running_stale_lease
            if result.snapshot is not None
            else None
        ),
        open_jobs_on_cancelled_run=(
            result.snapshot.open_jobs_on_cancelled_run
            if result.snapshot is not None
            else None
        ),
        last_terminal_job_at=result.last_terminal_job_at,
        age_seconds_since_last_terminal_job=result.age_seconds_since_last_terminal_job,
        stale_running_jobs=result.stale_running_jobs,
        backlog_without_active_lease=result.backlog_without_active_lease,
    )
