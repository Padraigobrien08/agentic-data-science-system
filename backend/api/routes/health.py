"""Liveness and dependency checks."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from backend import __version__
from backend.api.auth_deps import OpsTokenDep
from backend.api.deps import DbSession
from backend.config.settings import get_settings
from backend.llm.factory import describe_llm_runtime
from backend.observability.evaluation_validation import (
    get_evaluation_validation_observability,
)
from backend.observability.worker_queue import get_worker_queue_observability
from backend.schemas.health import (
    BackgroundDeliveryHealth,
    DatabaseHealth,
    EvaluationDependencyHealth,
    HealthResponse,
    LlmHealth,
    WorkerHealthResponse,
)

router = APIRouter()


def _health_status_for_evaluation(
    *,
    database_ok: bool,
    evaluation: EvaluationDependencyHealth,
) -> str:
    if not database_ok:
        return "degraded"
    if not evaluation.state_known:
        return "degraded"
    if evaluation.sec_dependency_ok is False or evaluation.storage_dependency_ok is False:
        return "degraded"
    return "ok"


def _background_delivery_health(
    *,
    settings,
    queue_result,
) -> BackgroundDeliveryHealth:
    if settings.chat_force_synchronous:
        return BackgroundDeliveryHealth(
            delivery_mode="sync_only",
            background_available=False,
            detail="Workspace chat is running synchronously while background delivery remains a secondary path.",
        )
    if not queue_result.queue_state_known:
        return BackgroundDeliveryHealth(
            delivery_mode="background_degraded",
            background_available=False,
            detail="Background delivery status is currently unavailable.",
        )
    if queue_result.stale_running_jobs:
        return BackgroundDeliveryHealth(
            delivery_mode="background_degraded",
            background_available=False,
            detail="Background delivery is degraded because a worker lease is stale.",
        )
    if queue_result.backlog_without_active_lease:
        return BackgroundDeliveryHealth(
            delivery_mode="background_degraded",
            background_available=False,
            detail="Background delivery is degraded because work is queued without an active worker lease.",
        )
    return BackgroundDeliveryHealth(
        delivery_mode="background_ready",
        background_available=True,
        detail=None,
    )


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
    queue_result = get_worker_queue_observability(
        db,
        max_attempts=settings.run_job_max_attempts,
    )
    evaluation_result = get_evaluation_validation_observability(db)
    evaluation = EvaluationDependencyHealth(
        state_known=evaluation_result.state_known,
        sec_dependency_ok=evaluation_result.sec_dependency_ok,
        storage_dependency_ok=evaluation_result.storage_dependency_ok,
        recent_degraded_case_count=evaluation_result.recent_degraded_case_count,
        detail=evaluation_result.detail,
    )
    return HealthResponse(
        status=_health_status_for_evaluation(database_ok=db_ok, evaluation=evaluation),
        version=__version__,
        database=DatabaseHealth(ok=db_ok, detail=detail),
        llm=LlmHealth(provider=lk, ready=lr, message=lm),
        evaluation=evaluation,
        background_delivery=_background_delivery_health(
            settings=settings,
            queue_result=queue_result,
        ),
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
    evaluation_result = get_evaluation_validation_observability(db)
    evaluation = EvaluationDependencyHealth(
        state_known=evaluation_result.state_known,
        sec_dependency_ok=evaluation_result.sec_dependency_ok,
        storage_dependency_ok=evaluation_result.storage_dependency_ok,
        recent_degraded_case_count=evaluation_result.recent_degraded_case_count,
        detail=evaluation_result.detail,
    )
    return WorkerHealthResponse(
        status=_health_status_for_evaluation(
            database_ok=result.database_ok,
            evaluation=evaluation,
        ),
        database=DatabaseHealth(
            ok=result.database_ok,
            detail=result.database_detail,
        ),
        evaluation=evaluation,
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
