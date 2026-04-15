---
phase: 02-worker-resilience
plan: 03
type: execute
wave: 3
depends_on:
  - 02-01
  - 02-02
files_modified:
  - tests/postgres_queue_test_utils.py
  - tests/test_backend_health.py
  - tests/test_worker_job_lifecycle_postgres.py
  - tests/test_worker_attempt_history.py
  - tests/test_worker_lease_heartbeat.py
  - tests/test_worker_job_lifecycle.py
  - tests/test_async_run_queue.py
  - tests/test_run_lifecycle_api.py
  - tests/test_run_lifecycle_production.py
autonomous: true
requirements:
  - WORK-01
  - WORK-02
must_haves:
  truths:
    - "Postgres claim/reclaim behavior proves one pending job cannot be claimed twice."
    - "Heartbeat, retry, reclaim, and cancellation semantics are locked by executable regressions."
    - "Status history regressions fail if attempt visibility or cancellation guarantees drift."
  artifacts:
    - path: tests/test_worker_job_lifecycle_postgres.py
      provides: "Real Postgres concurrency and stale-owner fencing coverage"
    - path: tests/test_worker_attempt_history.py
      provides: "Retry/reclaim history coverage on the same analysis_run_id"
    - path: tests/postgres_queue_test_utils.py
      provides: "Reusable isolated Postgres test database helper for worker queue semantics"
  key_links:
    - from: tests/test_worker_job_lifecycle_postgres.py
      to: backend/repositories/run_execution_job_repository.py
      via: "claim_next_runnable and renew/finalize fencing under Postgres"
      pattern: "claim_next_runnable|renew_lease|finalize_attempt_if_owned"
    - from: tests/test_worker_attempt_history.py
      to: backend/worker/loop.py
      via: "transient retry, stale reclaim, and cancellation regression coverage"
      pattern: "process_next_job"
    - from: tests/test_run_lifecycle_api.py
      to: backend/api/routes/runs.py
      via: "GET /status history assertions"
      pattern: "execution_job_history"
---

<objective>
Add the regression suites that prove the new lease fencing and attempt-history semantics hold under both the existing SQLite-style tests and real Postgres claim concurrency.

Purpose: Close the remaining verification gap for WORK-01 and WORK-02, especially the `SKIP LOCKED` behavior that SQLite cannot prove.
Output: Dedicated heartbeat/history tests plus a Postgres-backed queue-concurrency suite.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/02-worker-resilience/02-CONTEXT.md
@.planning/phases/02-worker-resilience/02-RESEARCH.md
@.planning/phases/02-worker-resilience/02-VALIDATION.md
@docs/local-stack.md
@backend/repositories/run_execution_job_repository.py
@backend/worker/loop.py
@tests/test_worker_job_lifecycle.py
@tests/test_run_lifecycle_api.py
@tests/test_async_run_queue.py
@tests/test_run_lifecycle_production.py

<interfaces>
From `backend/repositories/run_execution_job_repository.py`:
```python
def claim_next_runnable(*, lease_seconds: float, max_attempts: int) -> RunExecutionJob | None
def renew_lease(job_id: UUID, claim_token: str, lease_seconds: float) -> datetime
def finalize_attempt_if_owned(job_id: UUID, claim_token: str, *, status, error_detail=None) -> bool
```

From `backend/schemas/run_lifecycle.py`:
```python
class AnalysisRunStatusResponse(BaseModel):
    latest_execution_job: RunJobStatusSnapshot | None = None
    execution_job_history: list[RunJobStatusSnapshot] = []
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Add isolated Postgres claim/reclaim regression coverage</name>
  <files>tests/postgres_queue_test_utils.py, tests/test_worker_job_lifecycle_postgres.py</files>
  <read_first>.planning/phases/02-worker-resilience/02-RESEARCH.md
.planning/phases/02-worker-resilience/02-VALIDATION.md
docs/local-stack.md
backend/repositories/run_execution_job_repository.py
tests/test_worker_job_lifecycle.py</read_first>
  <action>Create `tests/postgres_queue_test_utils.py` with an isolated Postgres database helper that uses `EDGAR_TEST_POSTGRES_URL` when set and otherwise defaults to the Compose DSN `postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar`. The helper should create and tear down a unique temporary database per test module so queue tests do not share state with a developer’s normal DB. Add `tests/test_worker_job_lifecycle_postgres.py` to prove three concrete cases against PostgreSQL: exactly one of two concurrent sessions can claim the same pending row; stale queued reclaim rotates `claim_token` and the old token cannot renew or finalize; stale running reclaim creates the next pending attempt while the stale token can no longer complete the old row. Keep the file independent from FastAPI `TestClient` fixtures; this suite is about repository-level concurrency and ownership fencing.</action>
  <acceptance_criteria>`tests/postgres_queue_test_utils.py` exists and reads `EDGAR_TEST_POSTGRES_URL`.
`tests/test_worker_job_lifecycle_postgres.py` contains a concurrent double-claim test.
`tests/test_worker_job_lifecycle_postgres.py` asserts old `claim_token` renewal/finalization fails after reclaim.
The Postgres suite creates isolated test databases instead of writing into the default application schema.</acceptance_criteria>
  <verify>
    <automated>EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar python3 -m pytest tests/test_worker_job_lifecycle_postgres.py -q</automated>
  </verify>
  <done>The queue semantics that depend on PostgreSQL row locking and compare-and-set ownership are covered by an isolated Postgres regression suite.</done>
</task>

<task type="auto">
  <name>Task 2: Lock heartbeat, retry-history, and cancellation guarantees with focused regressions</name>
  <files>tests/test_backend_health.py, tests/test_worker_attempt_history.py, tests/test_worker_lease_heartbeat.py, tests/test_worker_job_lifecycle.py, tests/test_async_run_queue.py, tests/test_run_lifecycle_api.py, tests/test_run_lifecycle_production.py</files>
  <read_first>.planning/phases/02-worker-resilience/02-CONTEXT.md
.planning/phases/02-worker-resilience/02-VALIDATION.md
backend/api/routes/health.py
backend/observability/metrics.py
backend/worker/loop.py
backend/api/routes/runs.py
tests/test_backend_health.py
tests/test_worker_lease_heartbeat.py
tests/test_worker_job_lifecycle.py
tests/test_async_run_queue.py
tests/test_run_lifecycle_api.py
tests/test_run_lifecycle_production.py</read_first>
  <action>Create `tests/test_worker_attempt_history.py` with end-to-end regression cases for transient retry, stale-running reclaim, and manual retry so one `analysis_run_id` accumulates visible attempt rows in newest-first order. Update `tests/test_worker_lease_heartbeat.py` so it checks both heartbeat renewal and the `lease_lost` finalize path. Tighten the existing SQLite-backed suites so they assert old rows remain terminal, `/v1/runs/{run_id}/status` returns `execution_job_history`, and cancelled runs never gain a new pending row after failure or reclaim. Extend `tests/test_backend_health.py` so `/v1/worker/health` and `/metrics` continue to reflect the same truth as `queue_observability_snapshot()`: a pending row at the final allowed attempt still counts as claimable, exhausted attempts do not, stale running rows surface as stale, and backlog-without-active-lease flips only when that DB-backed condition is true. Keep the quick regression command aligned with `02-VALIDATION.md` by using the worker/job/status test modules already in the phase validation file plus the new attempt-history and backend-health suites.</action>
  <acceptance_criteria>`tests/test_worker_attempt_history.py` exists and covers transient retry, stale-running reclaim, and manual retry on one run id.
`tests/test_run_lifecycle_api.py` asserts `execution_job_history` is present and newest-first.
`tests/test_run_lifecycle_production.py` asserts cancelled runs do not auto-retry.
`tests/test_worker_lease_heartbeat.py` covers the `lease_lost` finalize branch.
`tests/test_backend_health.py` asserts `/v1/worker/health` and `/metrics` stay truthful for final-allowed pending attempts and stale-running leases.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_worker_attempt_history.py tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_run_lifecycle_api.py tests/test_run_lifecycle_production.py -q</automated>
  </verify>
  <done>The heartbeat, attempt-history, and cancellation guarantees are enforced by focused regression suites rather than only by implementation intent.</done>
</task>

</tasks>

<verification>
Run the SQLite-focused regression command after Task 2 and the Postgres concurrency suite after Task 1. If the local Postgres service is not already running, start the documented Compose `db` service before the Postgres verify command.
</verification>

<success_criteria>
Phase 02 is verification-ready when SQLite regressions and the isolated Postgres suite both prove that lease renewal, retry history, and worker reclaim behavior no longer permit duplicate execution or hidden attempts.
</success_criteria>

<output>
After completion, create `.planning/phases/02-worker-resilience/02-worker-resilience-03-SUMMARY.md`
</output>
