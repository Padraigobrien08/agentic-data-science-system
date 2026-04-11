"""
Prometheus metrics (``prometheus_client``). Scrape ``GET /metrics`` from the API process.

Vendor-neutral: any collector that speaks Prometheus text format works.
"""

from __future__ import annotations

import time
from typing import TYPE_CHECKING

from prometheus_client import Counter, Histogram

if TYPE_CHECKING:
    pass

# --- HTTP (populated by middleware) ---
HTTP_REQUESTS_TOTAL = Counter(
    "edgar_http_requests_total",
    "Total HTTP requests",
    ("method", "route", "status_class"),
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "edgar_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ("method", "route"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

# --- Analysis runs ---
ANALYSIS_RUN_TERMINAL_TOTAL = Counter(
    "edgar_analysis_run_terminal_total",
    "Analysis runs reaching a terminal DB status",
    ("status",),
)
PIPELINE_DURATION_SECONDS = Histogram(
    "edgar_pipeline_duration_seconds",
    "End-to-end pipeline execution time (orchestration + persistence)",
    ("outcome",),
    buckets=(1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
)
PIPELINE_ERRORS_TOTAL = Counter(
    "edgar_pipeline_errors_total",
    "Pipeline executions that raised before terminal persistence",
    ("error_type",),
)

# --- MCP (executor emits via log + optional counter from backend wrapper; executor sets counter in edgar) ---
# Counters from edgar_project would create import cycle; executor will call a small hook.
MCP_TOOL_CALLS_TOTAL = Counter(
    "edgar_mcp_tool_calls_total",
    "MCP tool invocations from orchestration executor",
    ("tool_name", "status"),
)

# --- LLM ---
LLM_COMPLETIONS_TOTAL = Counter(
    "edgar_llm_completions_total",
    "LLM chat completions (recorded agent calls)",
    ("agent_role", "status"),
)
LLM_COMPLETION_DURATION_SECONDS = Histogram(
    "edgar_llm_completion_duration_seconds",
    "LLM completion latency in seconds",
    ("agent_role",),
    buckets=(0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 30.0, 60.0, 120.0),
)

# --- Worker ---
WORKER_JOBS_TOTAL = Counter(
    "edgar_worker_jobs_total",
    "Worker job processing outcomes",
    ("outcome",),
)


def observe_http_request(method: str, route: str, status_code: int, duration_s: float) -> None:
    status_class = f"{status_code // 100}xx"
    HTTP_REQUESTS_TOTAL.labels(method=method, route=route, status_class=status_class).inc()
    HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=route).observe(duration_s)


def observe_pipeline_complete(duration_s: float, terminal_status: str) -> None:
    PIPELINE_DURATION_SECONDS.labels(outcome=terminal_status).observe(duration_s)
    ANALYSIS_RUN_TERMINAL_TOTAL.labels(status=terminal_status).inc()


def observe_pipeline_exception(exc: BaseException) -> None:
    PIPELINE_ERRORS_TOTAL.labels(error_type=type(exc).__name__).inc()


def observe_mcp_tool(tool_name: str, status: str) -> None:
    MCP_TOOL_CALLS_TOTAL.labels(tool_name=tool_name, status=status).inc()


def observe_llm_completion(agent_role: str, status: str, duration_s: float) -> None:
    LLM_COMPLETIONS_TOTAL.labels(agent_role=agent_role, status=status).inc()
    LLM_COMPLETION_DURATION_SECONDS.labels(agent_role=agent_role).observe(duration_s)


def observe_worker_job(outcome: str) -> None:
    WORKER_JOBS_TOTAL.labels(outcome=outcome).inc()


def monotonic_s() -> float:
    return time.perf_counter()
