---
phase: 05-storage-and-ops
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/observability/worker_queue.py
  - backend/api/routes/health.py
  - backend/schemas/health.py
  - backend/observability/metrics.py
  - tests/test_backend_health.py
autonomous: true
requirements:
  - OPER-01
must_haves:
  truths:
    - "Operators can tell the difference between an empty queue and an unknown queue state caused by failed DB-backed observability reads."
    - "`/v1/worker/health` returns an explicit degraded contract instead of substituting zero counts when queue reads fail."
    - "`/metrics` exposes explicit queue-observability health signals and does not silently zero-fill queue gauges on refresh failure."
  artifacts:
    - path: backend/observability/worker_queue.py
      provides: "Shared queue-observability result object used by JSON and Prometheus surfaces"
    - path: backend/schemas/health.py
      provides: "Worker-health schema that can represent known versus unknown queue state"
    - path: backend/observability/metrics.py
      provides: "Prometheus degraded-state gauges for queue observability"
    - path: tests/test_backend_health.py
      provides: "Regression coverage for degraded worker-health JSON and Prometheus NaN semantics"
  key_links:
    - from: backend/observability/worker_queue.py
      to: backend/api/routes/health.py
      via: "worker-health route converts the shared result into the API response"
      pattern: "get_worker_queue_observability|queue_state_known"
    - from: backend/observability/worker_queue.py
      to: backend/observability/metrics.py
      via: "metrics refresh uses the same DB-backed success or error result as worker health"
      pattern: "get_worker_queue_observability|edgar_worker_queue_observability_up"
---

<objective>
Make DB-backed worker-health and metrics surfaces report degraded dependency state explicitly instead of looking healthy when queue reads fail.

Purpose: satisfy `OPER-01` with one shared queue-observability contract so operators can trust `/v1/worker/health` and `/metrics` during outages.
Output: a shared observability helper, a nullable worker-health schema, explicit Prometheus degraded-state metrics, and backend regressions for the failure path.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/05-storage-and-ops/05-CONTEXT.md
@.planning/phases/05-storage-and-ops/05-RESEARCH.md
@.planning/phases/05-storage-and-ops/05-VALIDATION.md
@.planning/phases/02-worker-resilience/02-worker-resilience-03-SUMMARY.md
@.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md
@backend/repositories/run_execution_job_repository.py
@backend/api/routes/health.py
@backend/schemas/health.py
@backend/observability/metrics.py
@tests/test_backend_health.py
@docs/auth-api.md

<interfaces>
From `backend/repositories/run_execution_job_repository.py`:
```python
@dataclass(frozen=True, slots=True)
class WorkerQueueSnapshot:
    pending_claimable: int
    jobs_running_lease_ok: int
    jobs_running_stale_lease: int
    open_jobs_on_cancelled_run: int

def queue_observability_snapshot(self, *, max_attempts: int) -> WorkerQueueSnapshot: ...
def last_terminal_job_activity_at(self) -> datetime | None: ...
```

From `backend/schemas/health.py`:
```python
class WorkerHealthResponse(BaseModel):
    queue_depth: int
    jobs_running_lease_ok: int
    jobs_running_stale_lease: int
    open_jobs_on_cancelled_run: int
    last_terminal_job_at: datetime | None
    age_seconds_since_last_terminal_job: float | None
    stale_running_jobs: bool
    backlog_without_active_lease: bool
```

From `backend/observability/metrics.py`:
```python
def refresh_worker_queue_gauges_from_db(session: Session, *, max_attempts: int) -> None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Create one degraded-state queue observability contract for worker health</name>
  <files>backend/observability/worker_queue.py
backend/api/routes/health.py
backend/schemas/health.py
tests/test_backend_health.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
.planning/phases/02-worker-resilience/02-worker-resilience-03-SUMMARY.md
.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md
backend/repositories/run_execution_job_repository.py
backend/api/routes/health.py
backend/schemas/health.py
tests/test_backend_health.py
docs/auth-api.md</read_first>
  <behavior>
    - Per D-01, `GET /v1/worker/health` returns `status: "ok"` only when DB-backed queue reads succeed and `status: "degraded"` when they do not.
    - Per D-01 and D-02, unknown queue state is represented with `queue_state_known: false` and nullable counts or booleans, never synthetic zeroes or healthy-looking flags.
    - The successful worker-health path still derives counts from `RunExecutionJobRepository.queue_observability_snapshot(...)` and `last_terminal_job_activity_at()` so Phase 2 queue semantics stay canonical.
  </behavior>
  <action>Create a new helper module `backend/observability/worker_queue.py` with a dataclass such as `WorkerQueueObservabilityResult` plus a function `get_worker_queue_observability(session: Session, *, max_attempts: int) -> WorkerQueueObservabilityResult`. In that helper, call `RunExecutionJobRepository.queue_observability_snapshot(...)` and `last_terminal_job_activity_at()` once, compute `age_seconds_since_last_terminal_job` in UTC on success, and catch `SQLAlchemyError` to return `database_ok=False`, `database_detail=str(exc)`, `queue_state_known=False`, `snapshot=None`, and `last_terminal_job_at=None`. Update `backend/schemas/health.py` so `WorkerHealthResponse` has the exact additive fields `status: str`, `database: DatabaseHealth`, `queue_state_known: bool`, nullable queue counts (`int | None`), nullable backlog or stale flags (`bool | None`), and the existing timestamps. Update `backend/api/routes/health.py` to call the helper and map its result directly; do not leave the old `except SQLAlchemyError` branch that returns `queue_depth=0` or `stale_running_jobs=False`. Extend `tests/test_backend_health.py` with a degraded-path regression that forces the helper or repository call to raise `SQLAlchemyError` and then asserts `status == "degraded"`, `database.ok is False`, `queue_state_known is False`, `queue_depth is None`, and `backlog_without_active_lease is None`.</action>
  <acceptance_criteria>`backend/observability/worker_queue.py` exists and contains `class WorkerQueueObservabilityResult`.
`backend/schemas/health.py` contains `queue_state_known: bool`.
`backend/schemas/health.py` contains `queue_depth: int | None`.
`backend/schemas/health.py` contains `backlog_without_active_lease: bool | None`.
`backend/api/routes/health.py` contains `queue_state_known=result.queue_state_known` or an equivalent mapping from the shared helper result.
`backend/api/routes/health.py` no longer contains `queue_depth=0` in the `worker_health` failure path.
`tests/test_backend_health.py` contains `assert body["status"] == "degraded"`.
`tests/test_backend_health.py` contains `assert body["queue_state_known"] is False`.
`tests/test_backend_health.py` contains `assert body["queue_depth"] is None`.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py -q --tb=short</automated>
  </verify>
  <done>`/v1/worker/health` now reports queue-read degradation explicitly and distinguishes unknown queue state from a genuinely empty queue.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Make Prometheus queue metrics expose degraded-state truth instead of zero-fill</name>
  <files>backend/observability/metrics.py
tests/test_backend_health.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
backend/observability/worker_queue.py
backend/observability/metrics.py
backend/api/routes/metrics.py
tests/test_backend_health.py</read_first>
  <behavior>
    - Per D-01, `/metrics` publishes explicit queue-observability health signals when DB-backed refresh fails.
    - Per D-02, queue gauges represent unknown state as `NaN` instead of `0`, so alerts can distinguish dependency failure from an empty queue.
    - The degraded path remains aligned with the JSON worker-health helper instead of duplicating different truth logic.
  </behavior>
  <action>Refactor `backend/observability/metrics.py` to reuse `get_worker_queue_observability(...)` from the new helper. Add the exact gauges `edgar_worker_queue_observability_up` and `edgar_worker_queue_observability_last_error_unixtime`. On success, set `_up` to `1`, update `WORKER_QUEUE_DEPTH`, `WORKER_QUEUE_PENDING_CLAIMABLE`, `WORKER_QUEUE_JOBS_RUNNING_LEASE_OK`, `WORKER_QUEUE_JOBS_RUNNING_STALE_LEASE`, `WORKER_QUEUE_OPEN_ON_CANCELLED_RUN`, and `WORKER_LAST_TERMINAL_JOB_UNIXTIME` from the shared result, and leave the route contract in `backend/api/routes/metrics.py` unchanged. On degraded refresh, log `worker_queue_gauges_refresh_failed`, set `_up` to `0`, set `_last_error_unixtime` to `time.time()`, and set every queue or last-terminal gauge to `math.nan` instead of `0`. Extend `tests/test_backend_health.py` with a metrics failure-path regression that forces the helper to return degraded state, fetches `/metrics`, asserts `edgar_worker_queue_observability_up 0.0`, and parses `edgar_worker_queue_depth` and `edgar_worker_last_terminal_job_unixtime` as `NaN` via `math.isnan(...)`.</action>
  <acceptance_criteria>`backend/observability/metrics.py` contains `edgar_worker_queue_observability_up`.
`backend/observability/metrics.py` contains `edgar_worker_queue_observability_last_error_unixtime`.
`backend/observability/metrics.py` contains `.set(nan)` for queue or last-terminal gauges in the degraded branch.
`backend/observability/metrics.py` contains `get_worker_queue_observability(`.
`tests/test_backend_health.py` contains `edgar_worker_queue_observability_up`.
`tests/test_backend_health.py` contains `math.isnan(_metric_value(payload, "edgar_worker_queue_depth"))`.
`tests/test_backend_health.py` contains `math.isnan(_metric_value(payload, "edgar_worker_last_terminal_job_unixtime"))`.
`python3 -m pytest tests/test_backend_health.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py -q --tb=short</automated>
  </verify>
  <done>`/metrics` now makes dependency degradation explicit and never encodes unknown queue state as an empty queue.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_backend_health.py -q --tb=short` after each task so the worker-health JSON and Prometheus degraded-state semantics remain aligned through the same regression file.
</verification>

<success_criteria>
Phase 05 can trust its ops surface once `/v1/worker/health` and `/metrics` both show explicit degraded-state truth when queue reads fail, and fast regressions lock that behavior against future zero-fill regressions.
</success_criteria>

<output>
After completion, create `.planning/phases/05-storage-and-ops/05-storage-and-ops-01-SUMMARY.md`
</output>
