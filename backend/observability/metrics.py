"""
Prometheus metrics (``prometheus_client``).

* **API process** — scrape ``GET /metrics``; includes HTTP metrics and DB-backed worker **queue gauges**.
* **Worker process** — optional separate scrape target via ``EDGAR_BACKEND_WORKER_METRICS_PORT`` for
  attempt-level counters/histograms and loop liveness (see ``backend.worker``).
"""

from __future__ import annotations

import math
import time

import structlog
from prometheus_client import Counter, Gauge, Histogram
from sqlalchemy.orm import Session

from backend.observability.evaluation_validation import (
    get_evaluation_validation_observability,
)
from backend.observability.worker_queue import get_worker_queue_observability

_log = structlog.get_logger(__name__)

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

# --- Agentic investigation loop (populated by ``backend.observability.agent_observer``) ---
# Every label here is drawn from a closed enum (LoopComponent, TerminationReason,
# HypothesisStatus, InvestigationStatus) or the experiment registry's tool names, so
# label cardinality stays bounded.
AGENT_INVESTIGATIONS_TOTAL = Counter(
    "edgar_agent_investigations_total",
    "Investigations reaching a terminal loop status",
    ("status", "termination_reason"),
)
AGENT_INVESTIGATION_DURATION_SECONDS = Histogram(
    "edgar_agent_investigation_duration_seconds",
    "Wall time of one investigation loop call",
    ("status",),
    buckets=(0.5, 1.0, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0),
)
AGENT_INVESTIGATION_ITERATIONS = Histogram(
    "edgar_agent_investigation_iterations",
    "Loop iterations completed per investigation",
    buckets=(1, 2, 3, 5, 8, 13, 21, 34),
)
AGENT_COMPONENT_DURATION_SECONDS = Histogram(
    "edgar_agent_component_duration_seconds",
    "Decision latency of one loop component",
    ("component",),
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
)
AGENT_COMPONENT_ERRORS_TOTAL = Counter(
    "edgar_agent_component_errors_total",
    "Loop component invocations that raised",
    ("component", "error_type"),
)
AGENT_EXPERIMENTS_TOTAL = Counter(
    "edgar_agent_experiments_total",
    "Deterministic experiments executed by the loop",
    ("tool_name", "status"),
)
AGENT_EXPERIMENT_DURATION_SECONDS = Histogram(
    "edgar_agent_experiment_duration_seconds",
    "Deterministic experiment execution time",
    ("tool_name",),
    buckets=(0.005, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 15.0, 60.0),
)
AGENT_HYPOTHESIS_TRANSITIONS_TOTAL = Counter(
    "edgar_agent_hypothesis_transitions_total",
    "Hypothesis status changes (evidence actually moving a claim)",
    ("from_status", "to_status"),
)
AGENT_MODEL_CALLS_TOTAL = Counter(
    "edgar_agent_model_calls_total",
    "Model-backed policy decisions made by the loop",
    ("component",),
)
AGENT_COST_USD_TOTAL = Counter(
    "edgar_agent_cost_usd_total",
    "Estimated USD spent on loop policy decisions (0 for unpriced models)",
    ("component",),
)
AGENT_TERMINATIONS_TOTAL = Counter(
    "edgar_agent_terminations_total",
    "Typed termination decisions (why investigations stop)",
    ("reason",),
)

# --- Worker ---
WORKER_JOBS_TOTAL = Counter(
    "edgar_worker_jobs_total",
    "Worker job processing outcomes (coarse: completed, failed, requeued, cancelled, loop_error)",
    ("outcome",),
)

# Gauges refreshed from the DB on each API ``GET /metrics`` scrape (worker process not required).
WORKER_QUEUE_DEPTH = Gauge(
    "edgar_worker_queue_depth",
    "Jobs waiting to be claimed (pending, run queued, attempts remaining)",
)
WORKER_QUEUE_PENDING_CLAIMABLE = Gauge(
    "edgar_worker_queue_pending_claimable",
    "Pending jobs eligible for claim (run queued, attempts remaining)",
)
WORKER_QUEUE_JOBS_RUNNING_LEASE_OK = Gauge(
    "edgar_worker_queue_jobs_running_lease_ok",
    "Jobs in running status with a non-expired lease",
)
WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE = Gauge(
    "edgar_worker_queue_jobs_running_stale_lease",
    "Jobs in running status with missing or expired lease",
)
WORKER_QUEUE_OPEN_ON_CANCELLED_RUN = Gauge(
    "edgar_worker_queue_open_jobs_on_cancelled_run",
    "Open jobs (pending/running) tied to a cancelled run (cleanup backlog)",
)
WORKER_QUEUE_OBSERVABILITY_UP = Gauge(
    "edgar_worker_queue_observability_up",
    "1 when DB-backed worker queue observability is current, 0 when queue state is unknown",
)
WORKER_QUEUE_OBSERVABILITY_LAST_ERROR_UNIXTIME = Gauge(
    "edgar_worker_queue_observability_last_error_unixtime",
    "Unix time of the most recent worker queue observability refresh failure",
)
EVALUATION_DEPENDENCY_OBSERVABILITY_UP = Gauge(
    "edgar_evaluation_dependency_observability_up",
    "1 when DB-backed evaluation dependency observability is current, 0 when dependency state is unknown",
)
EVALUATION_SEC_DEPENDENCY_UP = Gauge(
    "edgar_evaluation_sec_dependency_up",
    "1 when recent evaluation SEC dependency state is healthy, 0 when degraded",
)
EVALUATION_STORAGE_DEPENDENCY_UP = Gauge(
    "edgar_evaluation_storage_dependency_up",
    "1 when recent evaluation storage dependency state is healthy, 0 when degraded",
)
EVALUATION_RECENT_DEGRADED_CASES = Gauge(
    "edgar_evaluation_recent_degraded_cases",
    "Recent live or hybrid evaluation cases carrying SEC or storage degradation evidence",
)

# Emitted from the worker process (scrape worker metrics port when enabled, or zero on API-only scrape).
WORKER_FINALIZE_OUTCOME_TOTAL = Counter(
    "edgar_worker_finalize_outcome_total",
    "Terminal disposition after a claimed job (fine-grained)",
    ("outcome",),
)
WORKER_JOB_WALL_DURATION_SECONDS = Histogram(
    "edgar_worker_job_wall_duration_seconds",
    "Wall time from successful claim commit through finalize (seconds)",
    ("finalize_outcome",),
    buckets=(0.5, 1.0, 2.5, 5.0, 15.0, 30.0, 60.0, 120.0, 300.0, 600.0, 1800.0, 3600.0),
)
WORKER_JOBS_CLAIMED_TOTAL = Counter(
    "edgar_worker_jobs_claimed_total",
    "Jobs successfully claimed from the queue (commit after claim)",
)
WORKER_JOBS_COMPLETED_TOTAL = Counter(
    "edgar_worker_jobs_completed_total",
    "Jobs finalized as completed (pipeline success, job row completed)",
)
WORKER_JOBS_FAILED_TOTAL = Counter(
    "edgar_worker_jobs_failed_total",
    "Jobs finalized as failed (terminal failure or requeue transition error)",
)
WORKER_JOBS_RETRIED_TOTAL = Counter(
    "edgar_worker_jobs_retried_total",
    "Jobs returned to pending after a transient pipeline failure",
)
WORKER_LOOP_LAST_TICK_UNIXTIME = Gauge(
    "edgar_worker_loop_last_tick_unixtime",
    "Unix time of the last worker poll loop iteration (liveness)",
)
WORKER_LAST_JOB_ACTIVITY_UNIXTIME = Gauge(
    "edgar_worker_last_job_activity_unixtime",
    "Unix time of last claim or finalized job attempt in this worker process",
)
WORKER_LAST_TERMINAL_JOB_UNIXTIME = Gauge(
    "edgar_worker_last_terminal_job_unixtime",
    "Unix time of last completed/failed/cancelled job row (from DB; API /metrics scrape)",
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


def mark_worker_job_activity() -> None:
    """Bump process-local job activity time (claim or finished attempt)."""
    WORKER_LAST_JOB_ACTIVITY_UNIXTIME.set(time.time())


def observe_worker_job_claimed() -> None:
    WORKER_JOBS_CLAIMED_TOTAL.inc()
    mark_worker_job_activity()


def refresh_worker_queue_gauges_from_db(session: Session, *, max_attempts: int) -> None:
    """Update queue depth gauges from the database (call during ``GET /metrics``)."""
    result = get_worker_queue_observability(session, max_attempts=max_attempts)
    if not result.queue_state_known or result.snapshot is None:
        _log.warning(
            "worker_queue_gauges_refresh_failed",
            worker_event="worker_queue_gauges_refresh_failed",
            error=result.database_detail,
        )
        WORKER_QUEUE_OBSERVABILITY_UP.set(0)
        WORKER_QUEUE_OBSERVABILITY_LAST_ERROR_UNIXTIME.set(time.time())
        for g in (
            WORKER_QUEUE_DEPTH,
            WORKER_QUEUE_PENDING_CLAIMABLE,
            WORKER_QUEUE_JOBS_RUNNING_LEASE_OK,
            WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE,
            WORKER_QUEUE_OPEN_ON_CANCELLED_RUN,
            WORKER_LAST_TERMINAL_JOB_UNIXTIME,
        ):
            g.set(math.nan)
        return

    WORKER_QUEUE_OBSERVABILITY_UP.set(1)
    snap = result.snapshot
    if result.last_terminal_job_at is not None:
        WORKER_LAST_TERMINAL_JOB_UNIXTIME.set(result.last_terminal_job_at.timestamp())
    else:
        WORKER_LAST_TERMINAL_JOB_UNIXTIME.set(0)
    WORKER_QUEUE_DEPTH.set(snap.pending_claimable)
    WORKER_QUEUE_PENDING_CLAIMABLE.set(snap.pending_claimable)
    WORKER_QUEUE_JOBS_RUNNING_LEASE_OK.set(snap.jobs_running_lease_ok)
    WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE.set(snap.jobs_running_stale_lease)
    WORKER_QUEUE_OPEN_ON_CANCELLED_RUN.set(snap.open_jobs_on_cancelled_run)


def refresh_evaluation_validation_gauges_from_db(
    session: Session,
    *,
    lookback_hours: int = 24,
) -> None:
    """Update evaluation dependency gauges from the database."""

    result = get_evaluation_validation_observability(
        session,
        lookback_hours=lookback_hours,
    )
    if not result.state_known:
        _log.warning(
            "evaluation_validation_gauges_refresh_failed",
            worker_event="evaluation_validation_gauges_refresh_failed",
            error=result.detail,
        )
        EVALUATION_DEPENDENCY_OBSERVABILITY_UP.set(0)
        for gauge in (
            EVALUATION_SEC_DEPENDENCY_UP,
            EVALUATION_STORAGE_DEPENDENCY_UP,
            EVALUATION_RECENT_DEGRADED_CASES,
        ):
            gauge.set(math.nan)
        return

    EVALUATION_DEPENDENCY_OBSERVABILITY_UP.set(1)
    EVALUATION_SEC_DEPENDENCY_UP.set(1 if result.sec_dependency_ok else 0)
    EVALUATION_STORAGE_DEPENDENCY_UP.set(1 if result.storage_dependency_ok else 0)
    EVALUATION_RECENT_DEGRADED_CASES.set(result.recent_degraded_case_count or 0)


def observe_worker_attempt_complete(
    *,
    finalize_outcome: str,
    coarse_outcome: str,
    wall_duration_s: float,
) -> None:
    """Record metrics after claim → pipeline → finalize (worker process)."""
    mark_worker_job_activity()
    WORKER_FINALIZE_OUTCOME_TOTAL.labels(outcome=finalize_outcome).inc()
    WORKER_JOB_WALL_DURATION_SECONDS.labels(finalize_outcome=finalize_outcome).observe(wall_duration_s)
    WORKER_JOBS_TOTAL.labels(outcome=coarse_outcome).inc()
    if finalize_outcome == "completed_success":
        WORKER_JOBS_COMPLETED_TOTAL.inc()
    elif finalize_outcome == "requeued_transient":
        WORKER_JOBS_RETRIED_TOTAL.inc()
    elif finalize_outcome in (
        "failed_run_still_queued",
        "failed_terminal_or_exhausted",
        "requeue_transition_failed",
    ):
        WORKER_JOBS_FAILED_TOTAL.inc()


def mark_worker_loop_tick() -> None:
    """Call once per worker poll iteration for a cheap liveness timestamp."""
    WORKER_LOOP_LAST_TICK_UNIXTIME.set(time.time())


def monotonic_s() -> float:
    return time.perf_counter()
