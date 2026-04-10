"""ASGI application factory."""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.engine.url import make_url

from backend import __version__
from backend.api.router import api_router
from backend.api.routes import health
from backend.config.settings import get_settings


def _ensure_database_parent_dir(database_url: str) -> None:
    """Create parent directory for file-backed SQLite so first connect does not fail."""
    url = make_url(database_url)
    if url.drivername != "sqlite" or not url.database:
        return
    path = Path(url.database)
    if not path.is_absolute():
        path = path.resolve()
    path.parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Startup: ensure SQLite parent dirs and artifact storage root exist."""
    s = get_settings()
    _ensure_database_parent_dir(s.database_url)
    s.artifact_storage_root.mkdir(parents=True, exist_ok=True)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        debug=settings.debug,
        lifespan=lifespan,
    )
    app.include_router(health.router, tags=["health"])
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
