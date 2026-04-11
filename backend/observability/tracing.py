"""
OpenTelemetry tracing (W3C ``traceparent`` / ``tracestate``).

* **API**: HTTP middleware continues incoming trace context and starts a server span.
* **Queue → worker**: :func:`serialize_trace_carrier` persists context on ``RunExecutionJob``;
  the worker calls :func:`attach_trace_carrier` so pipeline spans link to the same trace.
* **Exporters**: Set ``OTEL_EXPORTER_OTLP_ENDPOINT`` for OTLP HTTP, or
  ``OTEL_TRACES_EXPORTER=console`` for local debugging. Default is no exporter (no-op spans only
  if SDK is absent; with SDK, spans are dropped unless an exporter is configured).

Vendor-neutral: OTLP works with Jaeger, Grafana Tempo, Honeycomb, Datadog Agent, etc.
"""

from __future__ import annotations

import logging
import os
from collections.abc import Generator, Mapping
from contextlib import contextmanager
from typing import Any

from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.propagate import extract, inject, set_global_textmap
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator

log = logging.getLogger(__name__)

_TRACER_PROVIDER_CONFIGURED = False
_W3C_PROPAGATOR_SET = False


def _ensure_w3c_propagator() -> None:
    """Required for :func:`inject` / :func:`extract` (e.g. enqueue → worker handoff)."""
    global _W3C_PROPAGATOR_SET
    if _W3C_PROPAGATOR_SET:
        return
    set_global_textmap(TraceContextTextMapPropagator())
    _W3C_PROPAGATOR_SET = True


def setup_tracing(*, service_name: str | None = None) -> None:
    """
    Configure global tracer provider once (idempotent).

    Honors standard OTel env vars; optional app settings pass ``service_name``.
    """
    global _TRACER_PROVIDER_CONFIGURED
    _ensure_w3c_propagator()
    if _TRACER_PROVIDER_CONFIGURED:
        return

    name = service_name or os.getenv("OTEL_SERVICE_NAME") or "edgar-backend"
    exporter_mode = (os.getenv("OTEL_TRACES_EXPORTER") or os.getenv("EDGAR_BACKEND_OTEL_TRACES_EXPORTER") or "").lower()
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT") or os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")

    try:
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import (
            BatchSpanProcessor,
            ConsoleSpanExporter,
            SimpleSpanProcessor,
            SpanExporter,
            SpanExportResult,
        )
    except ImportError:
        log.debug("opentelemetry-sdk not installed; tracing uses no-op provider")
        _TRACER_PROVIDER_CONFIGURED = True
        return

    resource = Resource.create({"service.name": name})
    provider = TracerProvider(resource=resource)

    if endpoint:
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            log.info("OTel tracing: OTLP HTTP exporter → %s", endpoint)
        except ImportError:
            log.warning("OTLP endpoint set but opentelemetry-exporter-otlp not installed; skipping OTLP")
        except Exception as exc:  # noqa: BLE001
            log.warning("OTLP exporter init failed: %s", exc)
    elif exporter_mode == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
        log.info("OTel tracing: console exporter (OTEL_TRACES_EXPORTER=console)")
    elif exporter_mode not in ("none", "noop", "off"):
        # Without any processor, SDK spans have invalid context and W3C inject() is empty.
        class _VoidExporter(SpanExporter):
            def export(self, spans):  # noqa: ANN001
                return SpanExportResult.SUCCESS

            def shutdown(self) -> None:
                return None

            def force_flush(self, timeout_millis: int = 30000) -> bool:  # noqa: ARG002
                return True

        provider.add_span_processor(SimpleSpanProcessor(_VoidExporter()))
        log.debug("OTel tracing: spans not exported (set OTEL_EXPORTER_OTLP_ENDPOINT or OTEL_TRACES_EXPORTER=console)")

    trace.set_tracer_provider(provider)
    _TRACER_PROVIDER_CONFIGURED = True


def get_tracer(component: str, *, version: str = "1.0.0") -> trace.Tracer:
    """Tracer for a logical component (shown as instrumentation scope)."""
    return trace.get_tracer(component, version)


def serialize_trace_carrier() -> dict[str, str] | None:
    """
    Serialize current trace context for storage (e.g. on a queued job).

    Returns only W3C ``traceparent`` / ``tracestate`` keys when present.
    """
    _ensure_w3c_propagator()
    carrier: dict[str, str] = {}
    try:
        inject(carrier)
    except Exception:  # noqa: BLE001
        return None
    out: dict[str, str] = {}
    for k in ("traceparent", "tracestate"):
        v = carrier.get(k) or carrier.get(k.title())
        if v:
            out[k] = v
    return out or None


@contextmanager
def attach_trace_carrier(carrier: Mapping[str, Any] | None) -> Generator[None, None, None]:
    """
    Restore trace context from :func:`serialize_trace_carrier` (worker continuation).

    No-op when *carrier* is empty or invalid.
    """
    if not carrier:
        yield
        return
    _ensure_w3c_propagator()
    raw = {str(k).lower(): str(v) for k, v in carrier.items() if v is not None}
    if "traceparent" not in raw:
        yield
        return
    try:
        ctx = extract(raw)
    except Exception:  # noqa: BLE001
        yield
        return
    token = otel_context.attach(ctx)
    try:
        yield
    finally:
        otel_context.detach(token)


def bind_current_trace_for_logs() -> None:
    """Add ``trace_id`` / ``span_id`` to structlog contextvars from the active span (if valid)."""
    import structlog.contextvars
    from opentelemetry.trace import format_span_id, format_trace_id

    sc = trace.get_current_span().get_span_context()
    if not sc.is_valid:
        return
    structlog.contextvars.bind_contextvars(
        trace_id=format_trace_id(sc.trace_id),
        span_id=format_span_id(sc.span_id),
    )
