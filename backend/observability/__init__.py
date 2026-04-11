"""Structured logs, Prometheus metrics, and run correlation (contextvars)."""

from backend.observability.context import (
    bind_run_context,
    clear_run_context,
    merge_orchestration_run_id,
    run_context,
)
from backend.observability.install import install_edgar_telemetry_hooks
from backend.observability.logging import setup_observability_logging
from backend.observability.tracing import (
    attach_trace_carrier,
    bind_current_trace_for_logs,
    get_tracer,
    serialize_trace_carrier,
    setup_tracing,
)

__all__ = [
    "attach_trace_carrier",
    "bind_current_trace_for_logs",
    "bind_run_context",
    "clear_run_context",
    "get_tracer",
    "install_edgar_telemetry_hooks",
    "merge_orchestration_run_id",
    "run_context",
    "serialize_trace_carrier",
    "setup_observability_logging",
    "setup_tracing",
]
