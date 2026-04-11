"""Run ``python -m backend.worker`` to process queued analysis runs."""

from __future__ import annotations

import logging

from backend.config.settings import get_settings
from backend.db.session import SessionLocal
from backend.observability import install_edgar_telemetry_hooks, setup_observability_logging
from backend.observability.tracing import setup_tracing
from backend.worker.loop import run_forever


def main() -> None:
    settings = get_settings()
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    setup_observability_logging(level=level, json_logs=settings.observability_json_logs)
    setup_tracing(service_name=settings.otel_service_name)
    install_edgar_telemetry_hooks()
    if settings.worker_metrics_port > 0:
        from prometheus_client import start_http_server

        start_http_server(settings.worker_metrics_port)
        logging.getLogger(__name__).info(
            "worker_metrics_listen",
            extra={"worker_metrics_port": settings.worker_metrics_port},
        )
    run_forever(SessionLocal, poll_interval_s=settings.worker_poll_interval_s)


if __name__ == "__main__":
    main()
