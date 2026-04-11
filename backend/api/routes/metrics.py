"""Prometheus text exposition (no vendor-specific agents required)."""

from __future__ import annotations

from fastapi import APIRouter, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.api.deps import DbSession
from backend.config.settings import get_settings
from backend.observability.metrics import refresh_worker_queue_gauges_from_db

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
def prometheus_metrics(db: DbSession) -> Response:
    """OpenMetrics/Prometheus scrape endpoint."""
    settings = get_settings()
    refresh_worker_queue_gauges_from_db(db, max_attempts=settings.run_job_max_attempts)
    data = generate_latest()
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)
