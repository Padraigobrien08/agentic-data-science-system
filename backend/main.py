"""ASGI application factory."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy.engine.url import make_url

from backend import __version__
from backend.api.router import api_router
from backend.api.routes import health
from backend.api.routes import metrics as metrics_route
from backend.config.settings import get_settings, log_database_posture_once
from backend.observability import install_edgar_telemetry_hooks, setup_observability_logging
from backend.observability.middleware import ObservabilityMiddleware
from backend.observability.tracing import setup_tracing


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
    """Startup: logging, telemetry hooks, SQLite parent dirs, artifact storage root."""
    s = get_settings()
    level = getattr(logging, s.log_level.upper(), logging.INFO)
    setup_observability_logging(level=level, json_logs=s.observability_json_logs)
    log_database_posture_once(s)
    setup_tracing(service_name=s.otel_service_name)
    install_edgar_telemetry_hooks()
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
    app.add_middleware(ObservabilityMiddleware)
    app.include_router(health.router, tags=["health"])
    app.include_router(metrics_route.router)
    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app


app = create_app()
