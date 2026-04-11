"""FastAPI / Starlette middleware: request id, latency, Prometheus HTTP metrics, OTel server span."""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

import structlog.contextvars
from opentelemetry import context as otel_context
from opentelemetry import trace
from opentelemetry.propagate import extract, inject
from opentelemetry.trace import Status, StatusCode
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from backend.observability.context import reset_structlog_context
from backend.observability.metrics import observe_http_request
from backend.observability.tracing import bind_current_trace_for_logs, get_tracer, serialize_trace_carrier

# Paths excluded from detailed route template (metrics cardinality)
_METRICS_PATH = "/metrics"
_HEALTH_PATHS = frozenset({"/health", "/ready"})


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    if route is not None and hasattr(route, "path"):
        p = getattr(route, "path", None)
        if isinstance(p, str) and p:
            return p
    path = request.url.path
    if path == _METRICS_PATH:
        return "/metrics"
    if path in _HEALTH_PATHS:
        return path
    return path


class ObservabilityMiddleware(BaseHTTPMiddleware):
    """
    - Injects ``X-Request-ID`` (or echoes incoming header).
    - Binds ``request_id`` into structlog contextvars for the request.
    - Continues W3C trace context (``traceparent`` / ``tracestate``) and starts ``http.server.request``.
    - Injects ``traceparent`` on the response for downstream clients.
    - Records HTTP duration and status-class metrics.
    - Clears structlog contextvars after the response (prevents leakage across requests).
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        rid = request.headers.get("x-request-id") or str(uuid.uuid4())
        structlog.contextvars.bind_contextvars(request_id=rid)
        structlog.contextvars.bind_contextvars(component="api")

        method = request.method
        route = _route_template(request)
        t0 = time.perf_counter()

        carrier = {
            k.lower(): v
            for k, v in request.headers.items()
            if k.lower() in ("traceparent", "tracestate") and v
        }
        ctx_token = None
        if carrier:
            try:
                ctx_token = otel_context.attach(extract(carrier))
            except Exception:
                ctx_token = None

        skip_otel = route == _METRICS_PATH
        tracer = get_tracer("backend.http")

        async def _run_without_span() -> Response:
            return await call_next(request)

        try:
            if skip_otel:
                response = await _run_without_span()
            else:
                with tracer.start_as_current_span(
                    "http.server.request",
                    kind=trace.SpanKind.SERVER,
                    attributes={
                        "http.request.method": method,
                        "http.route": route,
                        "edgar.request_id": rid,
                    },
                ) as span:
                    bind_current_trace_for_logs()
                    # Sync route handlers run in a thread pool without OTel context; stash W3C carrier
                    # for enqueue → worker continuation (see RunQueueService / RunLifecycleService).
                    setattr(request.state, "trace_carrier_for_jobs", serialize_trace_carrier())
                    try:
                        response = await call_next(request)
                    except BaseException:
                        span.set_status(Status(StatusCode.ERROR))
                        raise
                    span.set_attribute("http.response.status_code", response.status_code)
                    out_c: dict[str, str] = {}
                    inject(out_c)
                    for hk, hv in out_c.items():
                        response.headers[hk] = hv
        except BaseException:
            duration = time.perf_counter() - t0
            if route != _METRICS_PATH:
                observe_http_request(method, route, 500, duration)
            reset_structlog_context()
            if ctx_token is not None:
                otel_context.detach(ctx_token)
            raise

        duration = time.perf_counter() - t0
        response.headers["X-Request-ID"] = rid
        if route != _METRICS_PATH:
            observe_http_request(method, route, response.status_code, duration)
        reset_structlog_context()
        if ctx_token is not None:
            otel_context.detach(ctx_token)
        return response
