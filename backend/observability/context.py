"""
Request/run correlation via :mod:`structlog` context variables.

All logs emitted while bound keys are set will include ``run_id`` (alias of
``analysis_run_id``), ``orchestration_run_id`` (orchestration ``run_id`` string),
``request_id``, and ``worker_job_id`` when provided. Use :func:`bind_run_context` at API/worker/pipeline
entrypoints and :func:`clear_run_context` in ``finally`` blocks.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any
from uuid import UUID

import structlog.contextvars

CORRELATION_KEYS = frozenset(
    {
        "request_id",
        "run_id",
        "analysis_run_id",
        "orchestration_run_id",
        "worker_job_id",
        "component",
        "trace_id",
        "span_id",
    }
)

# Unbound by :func:`clear_run_context` (pipeline / worker segments). ``trace_id`` / ``span_id`` stay
# for the remainder of the HTTP request until :func:`reset_structlog_context`.
_RUN_SEGMENT_KEYS = frozenset(
    {
        "request_id",
        "run_id",
        "analysis_run_id",
        "orchestration_run_id",
        "worker_job_id",
        "component",
        "from_worker",
    }
)


def bind_run_context(
    *,
    request_id: str | None = None,
    analysis_run_id: UUID | str | None = None,
    orchestration_run_id: str | None = None,
    worker_job_id: UUID | str | None = None,
    component: str | None = None,
    **extra: Any,
) -> None:
    """Merge correlation fields into the current context (thread/task-local)."""
    data: dict[str, Any] = {}
    if request_id is not None:
        data["request_id"] = request_id
    if analysis_run_id is not None:
        aid = str(analysis_run_id)
        data["analysis_run_id"] = aid
        data["run_id"] = aid
    if orchestration_run_id is not None:
        data["orchestration_run_id"] = orchestration_run_id
    if worker_job_id is not None:
        data["worker_job_id"] = str(worker_job_id)
    if component is not None:
        data["component"] = component
    for k, v in extra.items():
        if k in CORRELATION_KEYS or k.startswith("_"):
            continue
        data[k] = v
    if data:
        structlog.contextvars.bind_contextvars(**data)


def clear_run_context() -> None:
    """Remove run-scoped structlog keys (keep ``trace_id`` / ``span_id`` for the HTTP request)."""
    structlog.contextvars.unbind_contextvars(*_RUN_SEGMENT_KEYS)


def reset_structlog_context() -> None:
    """Clear all structlog contextvars (call once at end of HTTP request)."""
    structlog.contextvars.clear_contextvars()


def merge_orchestration_run_id(orchestration_run_id: str) -> None:
    """Attach orchestration ``run_id`` once the coordinator allocates it."""
    structlog.contextvars.bind_contextvars(orchestration_run_id=orchestration_run_id)


@contextmanager
def run_context(
    *,
    request_id: str | None = None,
    analysis_run_id: UUID | str | None = None,
    orchestration_run_id: str | None = None,
    worker_job_id: UUID | str | None = None,
    component: str | None = None,
) -> Iterator[None]:
    """Bind correlation for a block, then clear run keys (even on exception)."""
    bind_run_context(
        request_id=request_id,
        analysis_run_id=analysis_run_id,
        orchestration_run_id=orchestration_run_id,
        worker_job_id=worker_job_id,
        component=component,
    )
    try:
        yield
    finally:
        clear_run_context()
