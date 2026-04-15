---
phase: 02-worker-resilience
plan: 02
type: execute
wave: 2
depends_on:
  - 02-01
files_modified:
  - backend/config/settings.py
  - backend/models/run_execution_job.py
  - backend/repositories/run_execution_job_repository.py
  - backend/services/run_queue_service.py
  - backend/services/run_lifecycle_service.py
  - backend/schemas/run_lifecycle.py
  - backend/api/routes/runs.py
  - backend/worker/loop.py
  - tests/test_async_run_queue.py
  - tests/test_run_lifecycle_api.py
  - tests/test_run_lifecycle_production.py
  - tests/test_worker_job_lifecycle.py
autonomous: true
requirements:
  - WORK-02
must_haves:
  truths:
    - "Retries and stale-lease recovery stay attached to one `analysis_run_id` but do not erase prior attempts."
    - "A cancelled run never auto-retries, even after transient failure or lease expiry."
    - "Run status shows both the latest execution job and visible attempt history."
  artifacts:
    - path: backend/services/run_lifecycle_service.py
      provides: "Retry, cancel, and status assembly built around durable attempt rows"
    - path: backend/schemas/run_lifecycle.py
      provides: "Additive status response with attempt history"
    - path: tests/test_run_lifecycle_api.py
      provides: "API regression coverage for retry history visibility"
  key_links:
    - from: backend/worker/loop.py
      to: backend/repositories/run_execution_job_repository.py
      via: "requeue/reclaim creates a new pending attempt row instead of mutating the same row back to pending"
      pattern: "attempt_count.*\\+ 1|create_pending_attempt"
    - from: tests/test_worker_job_lifecycle.py
      to: backend/repositories/run_execution_job_repository.py
      via: "final allowed pending attempt stays claimable and queue observability matches the same comparator"
      pattern: "claim_next_runnable|queue_observability_snapshot"
    - from: backend/services/run_lifecycle_service.py
      to: backend/schemas/run_lifecycle.py
      via: "build_status_view populates latest job plus history"
      pattern: "execution_job_history"
    - from: backend/api/routes/runs.py
      to: backend/services/run_lifecycle_service.py
      via: "GET /v1/runs/{run_id}/status uses the additive history response"
      pattern: "build_status_view"
---

<objective>
Convert retries and stale-lease recovery into durable attempt history on the same run and surface that history through the existing run-centric status API.

Purpose: Satisfy D-02, D-03, D-04, and WORK-02 without introducing new run identities or breaking the current `/status` route.
Output: One `RunExecutionJob` row per attempt, no auto-retry after cancellation, and additive status history.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-worker-resilience/02-CONTEXT.md
@.planning/phases/02-worker-resilience/02-RESEARCH.md
@.planning/phases/02-worker-resilience/02-worker-resilience-01-PLAN.md
@backend/models/run_execution_job.py
@backend/repositories/run_execution_job_repository.py
@backend/services/run_queue_service.py
@backend/services/run_lifecycle_service.py
@backend/schemas/run_lifecycle.py
@backend/api/routes/runs.py
@backend/worker/loop.py

<interfaces>
From `backend/services/run_queue_service.py`:
```python
def enqueue_after_create(
    self,
    analysis_run_id: UUID,
    overrides: dict[str, Any] | None,
    *,
    trace_carrier: dict[str, str] | None = None,
) -> None
```

From `backend/services/run_lifecycle_service.py`:
```python
def retry_analysis_run(
    self,
    analysis_run_id: UUID,
    *,
    overrides: dict[str, Any] | None = None,
    trace_carrier: dict[str, str] | None = None,
) -> AnalysisRun

def build_status_view(
    self,
    analysis_run_id: UUID,
) -> tuple[AnalysisRun, bool, RunExecutionJob | None]
```

From `backend/schemas/run_lifecycle.py`:
```python
class AnalysisRunStatusResponse(BaseModel):
    analysis_run_id: UUID
    has_open_execution_job: bool
    latest_execution_job: RunJobStatusSnapshot | None = None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make each retry or stale reclaim create a new attempt row on the same run</name>
  <files>backend/config/settings.py, backend/models/run_execution_job.py, backend/repositories/run_execution_job_repository.py, backend/services/run_queue_service.py, backend/services/run_lifecycle_service.py, backend/worker/loop.py, tests/test_worker_job_lifecycle.py, tests/test_async_run_queue.py, tests/test_run_lifecycle_production.py</files>
  <read_first>.planning/phases/02-worker-resilience/02-CONTEXT.md
.planning/phases/02-worker-resilience/02-RESEARCH.md
.planning/phases/02-worker-resilience/02-worker-resilience-01-PLAN.md
backend/config/settings.py
backend/models/run_execution_job.py
backend/repositories/run_execution_job_repository.py
backend/services/run_queue_service.py
backend/services/run_lifecycle_service.py
backend/worker/loop.py
tests/test_worker_job_lifecycle.py
tests/test_async_run_queue.py
tests/test_run_lifecycle_production.py</read_first>
  <behavior>
    - The initial enqueue path creates attempt `1`, and claiming that pending row does not increment it again.
    - A pending row whose `attempt_count == max_attempts` is still claimable because it already represents the final allowed attempt.
    - A transient worker failure leaves the failed attempt row intact and inserts a new pending attempt row with `attempt_count == previous + 1`.
    - Stale-lease recovery after `AnalysisRun.status == running` follows the same pattern, while cancelled runs never create a replacement pending row.
  </behavior>
  <action>Change the semantics of `RunExecutionJob` to one durable row per execution attempt. Update the `backend/models/run_execution_job.py` docstring and the `attempt_count` field doc to describe it as the 1-based attempt number for that row. In `backend/config/settings.py`, change `run_job_max_attempts` documentation to describe a per-run attempt ceiling rather than increments on one mutable row. In `RunQueueService.enqueue_after_create()`, create the initial pending job with `attempt_count=1`, `claim_token=None`, and `lease_expires_at=None`. In `RunLifecycleService.retry_analysis_run()`, create a new pending row with `attempt_count = latest.attempt_count + 1` for the same `analysis_run_id` instead of resetting to `0`. In `RunExecutionJobRepository.claim_next_runnable()`, stop incrementing `attempt_count` on fresh claim and update the fresh-claim comparator so a pending row with `attempt_count <= max_attempts` is still runnable, including the final allowed attempt where `attempt_count == max_attempts`. Apply the same inclusive comparator to `queue_observability_snapshot()` so metrics and `/v1/worker/health` report the same claimable set as the repository. On stale-running reclaim with attempts remaining, mark the current row `failed`, clear `lease_expires_at` and `claim_token`, set `error_detail` to the literal `lease_expired_mid_run`, transition the run `error -> queued`, and insert a new pending row with `attempt_count = current.attempt_count + 1`; if the max-attempt ceiling is already reached, leave no new pending row. In `_finalize_job_after_attempt()`, change transient-failure retry scheduling so it marks the current row `failed`, clears `claim_token`, and inserts a new pending row instead of mutating the same row back to `pending`. Every auto-retry branch must first re-check `run.status != AnalysisRunStatus.cancelled` per D-04. Update the worker/service tests first so they prove the prior attempt row remains terminal and the next attempt row is a new DB row on the same `analysis_run_id` per D-02 and D-03, and add regression coverage for `max_attempts=1`, a pending row already at `attempt_count == max_attempts`, and queue observability matching the same claimability rule.</action>
  <acceptance_criteria>`backend/services/run_queue_service.py` sets `attempt_count=1` on first enqueue.
`backend/repositories/run_execution_job_repository.py` no longer increments `attempt_count` in the fresh-claim branch.
`claim_next_runnable()` treats a pending row with `attempt_count == max_attempts` as the final allowed runnable attempt instead of skipping it.
`queue_observability_snapshot()` uses the same inclusive pending-attempt comparator as `claim_next_runnable()`.
Transient failure and stale-running reclaim branches create a new pending `RunExecutionJob` row with `attempt_count` one higher than the failed row.
Cancelled runs have no branch that inserts a new pending row after a failure or stale reclaim.
`tests/test_worker_job_lifecycle.py`, `tests/test_async_run_queue.py`, and `tests/test_run_lifecycle_production.py` assert that prior attempt rows remain terminal instead of returning to `pending`, including `max_attempts=1` and `attempt_count == max_attempts` claimability cases.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_run_lifecycle_production.py -q</automated>
  </verify>
  <done>Every retry path preserves the old attempt row, creates the next pending attempt on the same run when allowed, and never auto-retries a cancelled run.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Expose latest attempt plus durable execution history in the status API</name>
  <files>backend/repositories/run_execution_job_repository.py, backend/services/run_lifecycle_service.py, backend/schemas/run_lifecycle.py, backend/api/routes/runs.py, tests/test_run_lifecycle_api.py, tests/test_run_lifecycle_production.py</files>
  <read_first>.planning/phases/02-worker-resilience/02-CONTEXT.md
.planning/phases/02-worker-resilience/02-RESEARCH.md
backend/repositories/run_execution_job_repository.py
backend/services/run_lifecycle_service.py
backend/schemas/run_lifecycle.py
backend/api/routes/runs.py
tests/test_run_lifecycle_api.py
tests/test_run_lifecycle_production.py</read_first>
  <behavior>
    - `/v1/runs/{run_id}/status` keeps `latest_execution_job` but also returns ordered `execution_job_history`.
    - The first history item always matches `latest_execution_job`.
    - Status history shows both failed prior attempts and the current pending/running/latest attempt for one `analysis_run_id`.
  </behavior>
  <action>Add `RunExecutionJobRepository.list_for_run(analysis_run_id, *, limit: int | None = None)` ordered by `attempt_count DESC, created_at DESC`. Extend `RunLifecycleService.build_status_view()` so it returns `row`, `has_open`, `latest`, and `history` instead of only the latest row. In `backend/schemas/run_lifecycle.py`, keep `latest_execution_job` unchanged, keep the field name `attempt_count` for backward compatibility, and add `execution_job_history: list[RunJobStatusSnapshot] = []` to `AnalysisRunStatusResponse`. Update `analysis_run_status_to_response()` and `backend/api/routes/runs.py::get_run_status()` to populate the new field without removing any current fields. Add API tests that create at least two attempt rows for the same run, then assert `/status` returns them newest-first, `latest_execution_job["attempt_count"]` equals the first history item, and cancelled runs expose cancelled latest/history rows with no pending replacement.</action>
  <acceptance_criteria>`backend/repositories/run_execution_job_repository.py` defines `list_for_run(`.
`backend/schemas/run_lifecycle.py` defines `execution_job_history`.
`AnalysisRunStatusResponse` still includes `latest_execution_job`.
`backend/api/routes/runs.py` returns `execution_job_history` from `/v1/runs/{run_id}/status`.
`tests/test_run_lifecycle_api.py` proves history is ordered newest-first and additive to the existing response contract.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_run_lifecycle_api.py tests/test_run_lifecycle_production.py -q</automated>
  </verify>
  <done>The status API stays run-centric but now makes retry and reclaim attempts clearly visible for operators on the same `analysis_run_id`.</done>
</task>

</tasks>

<verification>
After Task 1, confirm no retry path mutates an existing failed attempt back to `pending`. After Task 2, confirm `/status` remains backward-compatible by keeping `latest_execution_job` while adding the new history list.
</verification>

<success_criteria>
`WORK-02` is implementation-ready when retries and stale recovery keep one run identity, every attempt is durable and visible, and cancelled runs remain terminal with no automatic requeue.
</success_criteria>

<output>
After completion, create `.planning/phases/02-worker-resilience/02-worker-resilience-02-SUMMARY.md`
</output>
