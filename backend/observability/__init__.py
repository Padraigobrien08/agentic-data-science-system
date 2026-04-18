"""Structured logs, telemetry hooks, and run correlation helpers."""

from __future__ import annotations

from importlib import import_module

from backend.observability.context import (
    bind_run_context,
    clear_run_context,
    merge_orchestration_run_id,
    run_context,
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


def __getattr__(name: str):
    if name == "install_edgar_telemetry_hooks":
        return import_module("backend.observability.install").install_edgar_telemetry_hooks
    if name == "setup_observability_logging":
        return import_module("backend.observability.logging").setup_observability_logging
    if name in {
        "attach_trace_carrier",
        "bind_current_trace_for_logs",
        "get_tracer",
        "serialize_trace_carrier",
        "setup_tracing",
    }:
        tracing = import_module("backend.observability.tracing")
        return getattr(tracing, name)
    raise AttributeError(name)
