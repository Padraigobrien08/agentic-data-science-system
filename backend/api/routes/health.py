"""Liveness and dependency checks."""

from fastapi import APIRouter
from sqlalchemy import text

from backend import __version__
from backend.api.deps import DbSession
from backend.schemas.health import DatabaseHealth, HealthResponse

router = APIRouter()


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
