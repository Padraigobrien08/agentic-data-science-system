---
phase: 02-worker-resilience
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - alembic/versions/006_run_job_claim_token.py
  - backend/agents/traceable_analysis_pipeline.py
  - backend/models/run_execution_job.py
  - backend/repositories/run_execution_job_repository.py
  - backend/services/exceptions.py
  - backend/services/edgar_pipeline_execution_service.py
  - backend/worker/lease.py
  - backend/worker/loop.py
  - edgar_project/orchestration/executor.py
  - tests/test_worker_job_lifecycle.py
  - tests/test_worker_lease_heartbeat.py
autonomous: true
requirements:
  - WORK-01
must_haves:
  truths:
    - "A running worker renews its lease while work is still active instead of relying on one static long lease."
    - "A worker that lost ownership cannot renew or finalize a reclaimed job."
    - "Lease loss aborts before output persistence or terminal run/job writes."
  artifacts:
    - path: backend/worker/lease.py
      provides: "Background heartbeat guard with ownership-loss detection"
    - path: backend/repositories/run_execution_job_repository.py
      provides: "Claim, renew, and finalize compare-and-set helpers keyed by claim_token"
    - path: tests/test_worker_lease_heartbeat.py
      provides: "Regression coverage for heartbeat renewal and lost-ownership aborts"
  key_links:
    - from: backend/worker/loop.py
      to: backend/worker/lease.py
      via: "WorkerLeaseGuard lifecycle around process_next_job"
      pattern: "WorkerLeaseGuard"
    - from: backend/worker/lease.py
      to: backend/repositories/run_execution_job_repository.py
      via: "compare-and-set renew/finalize helpers"
      pattern: "renew_lease|finalize_attempt_if_owned"
    - from: backend/services/edgar_pipeline_execution_service.py
      to: backend/worker/lease.py
      via: "execution_checkpoint callback before persistence boundaries"
      pattern: "execution_checkpoint"
    - from: backend/services/edgar_pipeline_execution_service.py
      to: edgar_project/orchestration/executor.py
      via: "execution checkpoints propagate into orchestration/tool dispatch, not only outer worker boundaries"
      pattern: "execution_checkpoint|checkpoint"
---

<objective>
Add fenced lease ownership and active heartbeat behavior so long-running jobs stay owned safely and stale workers cannot complete a superseded attempt.

Purpose: Satisfy D-01 and the WORK-01 duplicate-execution boundary before retry/history changes build on top of it.
Output: A claim-token-backed lease contract, worker heartbeat helper, and lost-lease regression coverage.
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
@.planning/phases/02-worker-resilience/02-CONTEXT.md
@.planning/phases/02-worker-resilience/02-RESEARCH.md
@.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
@backend/models/run_execution_job.py
@backend/repositories/run_execution_job_repository.py
@backend/worker/loop.py
@backend/services/edgar_pipeline_execution_service.py
@backend/services/exceptions.py
@alembic/versions/005_run_job_attempts_lease.py

<interfaces>
From `backend/repositories/run_execution_job_repository.py`:
```python
def claim_next_runnable(*, lease_seconds: float, max_attempts: int) -> RunExecutionJob | None
```

From `backend/worker/loop.py`:
```python
def process_next_job(
    session_factory: Callable[[], Session],
    *,
    lease_seconds: float | None = None,
    max_attempts: int | None = None,
) -> bool
```

From `backend/services/edgar_pipeline_execution_service.py`:
```python
def execute_analysis_run(
    self,
    analysis_run_id: UUID,
    *,
    tickers: list[str] | None = None,
    analysis_goal: str | None = None,
    refresh: bool | None = None,
    from_worker: bool = False,
) -> OrchestrationOutput
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add claim-token ownership fencing to queued job claims</name>
  <files>alembic/versions/006_run_job_claim_token.py, backend/models/run_execution_job.py, backend/repositories/run_execution_job_repository.py, backend/services/exceptions.py, tests/test_worker_job_lifecycle.py</files>
  <read_first>.planning/phases/02-worker-resilience/02-CONTEXT.md
.planning/phases/02-worker-resilience/02-RESEARCH.md
.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
alembic/versions/005_run_job_attempts_lease.py
backend/models/run_execution_job.py
backend/repositories/run_execution_job_repository.py
backend/services/exceptions.py
tests/test_worker_job_lifecycle.py</read_first>
  <behavior>
    - Claiming any fresh or stale runnable job writes a fresh non-null `claim_token` on the returned running row.
    - Reclaiming a stale queued job rotates `claim_token` without incrementing `attempt_count`.
    - Renew or finalize operations fail when `job_id`, `status == running`, and `claim_token` no longer match the current owner row.
  </behavior>
  <action>Add a new Alembic revision `006_run_job_claim_token.py` that adds nullable `claim_token` to `run_execution_jobs`. Update `RunExecutionJob` so the model includes `claim_token: Mapped[str | None]` and document it as the ownership fence for post-claim work. In `backend/services/exceptions.py`, add a dedicated `WorkerLeaseLostError(Exception)` for lost ownership. In `RunExecutionJobRepository`, change every branch of `claim_next_runnable()` that returns a running job so it writes a new UUID-like string token, sets `claimed_at`, and sets `lease_expires_at`; never return a running row with `claim_token is None`. Add `renew_lease(job_id, claim_token, lease_seconds)` that extends `lease_expires_at` only when `id`, `status == RunExecutionJobStatus.running`, and `claim_token` still match, raising `WorkerLeaseLostError` on a zero-row update. Add `finalize_attempt_if_owned(job_id, claim_token, *, status, error_detail=None)` that clears `lease_expires_at` and `claim_token`, applies the terminal status, and returns `False` instead of mutating anything when ownership no longer matches. Update `tests/test_worker_job_lifecycle.py` first so it proves fresh claims set `claim_token`, stale queued reclaim rotates the token, and a mismatched token cannot renew the lease. Implement per D-01 and keep the existing zombie-cancel cleanup branch intact.</action>
  <acceptance_criteria>`backend/models/run_execution_job.py` defines `claim_token`.
`alembic/versions/006_run_job_claim_token.py` exists and adds `claim_token` on `run_execution_jobs`.
`backend/repositories/run_execution_job_repository.py` contains `def renew_lease(` and `def finalize_attempt_if_owned(`.
`claim_next_runnable()` writes a non-null `claim_token` in every branch that returns a running job.
`tests/test_worker_job_lifecycle.py` asserts token rotation on stale queued reclaim and renewal failure on token mismatch.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_worker_job_lifecycle.py -q</automated>
  </verify>
  <done>Claimed jobs are fenced by `claim_token`, stale owners cannot renew/finalize them, and the repository contract is covered by executable tests.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Heartbeat active worker leases and abort safely on ownership loss</name>
  <files>backend/worker/lease.py, backend/worker/loop.py, backend/services/edgar_pipeline_execution_service.py, backend/agents/traceable_analysis_pipeline.py, edgar_project/orchestration/executor.py, backend/repositories/run_execution_job_repository.py, backend/services/exceptions.py, tests/test_worker_lease_heartbeat.py</files>
  <read_first>.planning/phases/02-worker-resilience/02-CONTEXT.md
.planning/phases/02-worker-resilience/02-RESEARCH.md
backend/repositories/run_execution_job_repository.py
backend/services/exceptions.py
backend/services/edgar_pipeline_execution_service.py
backend/agents/traceable_analysis_pipeline.py
edgar_project/orchestration/executor.py
backend/worker/loop.py
tests/test_worker_job_lifecycle.py</read_first>
  <behavior>
    - A mocked long-running worker attempt keeps `lease_expires_at` moving forward while the pipeline is still in progress.
    - If heartbeats stop owning the row, the worker raises `WorkerLeaseLostError` before payload persistence and artifact ingestion.
    - If ownership is lost during orchestration, the stale worker aborts before any subsequent MCP tool dispatch or terminal persistence step.
    - Finalization returns a non-success outcome when the job was already reclaimed instead of overwriting the newer owner’s state.
  </behavior>
  <action>Create `backend/worker/lease.py` with a `WorkerLeaseGuard` helper that uses a fresh DB session from `session_factory`, renews the lease every `min(max(lease_seconds / 3.0, 5.0), 60.0)` seconds, and records lost ownership when `renew_lease()` raises `WorkerLeaseLostError`. The helper must expose `checkpoint()` that raises `WorkerLeaseLostError` immediately after any lost-ownership signal. Update `process_next_job()` to start `WorkerLeaseGuard` right after the claim commit, pass `guard.checkpoint` into `EdgarPipelineExecutionService.execute_analysis_run(...)`, and stop the guard in `finally` before finalization. Extend `execute_analysis_run()` with optional `execution_checkpoint: Callable[[], None] | None = None`, then thread that callback through `run_traceable_edgar_pipeline`, `backend/agents/traceable_analysis_pipeline.py`, and `edgar_project/orchestration/executor.py` so it runs at the existing safe boundaries plus immediately before each MCP tool dispatch / orchestration step transition. Keep the outer worker checkpoints as well: immediately after switching the run to `running`, immediately before invoking `run_traceable_edgar_pipeline`, immediately after orchestration returns, immediately before `set_output_payload`, immediately before artifact ingestion, and immediately before the final `transition_status`. Update `_finalize_job_after_attempt()` so every terminal mutation uses `finalize_attempt_if_owned(job_id, claim_token, ...)`; if ownership is already lost, return the literal finalize outcome `lease_lost` and do not mutate the superseded row or run. Add `tests/test_worker_lease_heartbeat.py` first to cover heartbeat renewal during a deliberately delayed pipeline, plus a reclaim-during-orchestration regression that proves the stale worker aborts before any subsequent MCP tool call, payload persistence, artifact ingestion, or terminal write. Keep D-01 strict: the normal path is active heartbeat, not a longer static lease.</action>
  <acceptance_criteria>`backend/worker/lease.py` exists and defines `WorkerLeaseGuard`.
`backend/services/edgar_pipeline_execution_service.py` accepts `execution_checkpoint`.
`execution_checkpoint()` is threaded into `backend/agents/traceable_analysis_pipeline.py` and `edgar_project/orchestration/executor.py` so ownership is checked before inner orchestration/tool-dispatch side effects as well as before persistence boundaries.
`execute_analysis_run()` calls `execution_checkpoint()` before orchestration, before payload persistence, before artifact ingestion, and before terminal status persistence.
`backend/worker/loop.py` passes the claimed `claim_token` into finalization and returns `lease_lost` when ownership is gone.
`tests/test_worker_lease_heartbeat.py` covers lease renewal during a delayed pipeline and ownership-loss abort behavior, including a mid-orchestration reclaim case.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_worker_job_lifecycle.py tests/test_worker_lease_heartbeat.py -q</automated>
  </verify>
  <done>Long-running worker jobs renew their lease in the background, execution checkpoints abort when ownership is lost, and stale workers cannot finalize reclaimed attempts.</done>
</task>

</tasks>

<verification>
Run the worker lease suites after each task. If Task 2 introduces a new finalize outcome such as `lease_lost`, confirm the existing metrics/logging paths tolerate the new label without extra schema changes.
</verification>

<success_criteria>
`WORK-01` is implementation-ready when every claimed running job has a `claim_token`, the worker keeps leases fresh during long work, and a stale owner can neither renew nor finalize a superseded attempt.
</success_criteria>

<output>
After completion, create `.planning/phases/02-worker-resilience/02-worker-resilience-01-SUMMARY.md`
</output>
