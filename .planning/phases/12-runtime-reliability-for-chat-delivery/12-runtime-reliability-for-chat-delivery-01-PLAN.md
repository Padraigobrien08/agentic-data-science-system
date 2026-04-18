---
phase: 12-runtime-reliability-for-chat-delivery
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/services/__init__.py
  - tests/test_worker_runtime_boot.py
  - scripts/smoke-compose.sh
  - tests/test_async_run_queue.py
  - tests/test_worker_job_lifecycle.py
autonomous: true
requirements:
  - RUN-01
  - RUN-02
must_haves:
  truths:
    - "The worker process can boot in the documented local stack without hitting the current `backend.observability.metrics` ↔ `backend.services` circular import."
    - "Queued execution still uses the existing queue and worker lifecycle instead of introducing a second runtime path."
    - "The documented stack smoke path proves both synchronous execution and worker-claimed queued execution no longer fail on run-workspace/runtime setup gaps."
  artifacts:
    - path: backend/services/__init__.py
      provides: "A lightweight service package surface that no longer imports the pipeline/LLM stack during worker boot"
    - path: tests/test_worker_runtime_boot.py
      provides: "Regression coverage for the worker boot/import path"
    - path: scripts/smoke-compose.sh
      provides: "Stack-level smoke contract for synchronous and queued run execution"
  key_links:
    - from: backend/services/__init__.py
      to: backend/worker/__main__.py
      via: "worker startup no longer drags the heavy pipeline service graph into package import time"
      pattern: "AnalysisRunService|ArtifactService|RunStepService|ToolCallService"
    - from: scripts/smoke-compose.sh
      to: backend/api/routes/runs.py
      via: "the smoke script exercises both `POST /v1/runs/{id}/execute` and queued `POST /v1/runs` flows against the live stack"
      pattern: "/v1/runs|/execute|/status"
    - from: tests/test_worker_runtime_boot.py
      to: backend/worker/__main__.py
      via: "tests lock the import path that previously failed before the worker loop could start"
      pattern: "backend.worker.__main__|backend.worker.loop|backend.observability.metrics"
---

<objective>
Repair the worker/runtime foundation for the documented local stack and lock the existing run-workspace fix into an explicit smoke and regression contract.

Purpose: satisfy the runtime half of Phase 12 before chat becomes sync-first by ensuring the worker can boot and queued runs can still be claimed in Compose.
Output: worker import-cycle repair, worker boot regression coverage, and a stronger compose smoke path for sync plus queued execution.
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
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
@.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
@backend/services/__init__.py
@backend/worker/__main__.py
@backend/worker/loop.py
@backend/observability/metrics.py
@backend/services/recorded_chat_completion_service.py
@backend/repositories/run_execution_job_repository.py
@docker-entrypoint.sh
@scripts/smoke-compose.sh
@tests/test_async_run_queue.py
@tests/test_worker_job_lifecycle.py
@tests/test_worker_lease_heartbeat.py

<interfaces>
From `backend/worker/__main__.py`:
```python
from backend.observability import install_edgar_telemetry_hooks, setup_observability_logging
from backend.worker.loop import run_forever
```

From `backend/services/recorded_chat_completion_service.py`:
```python
from backend.observability.metrics import observe_llm_completion
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Remove the worker boot circular import at the service package boundary</name>
  <files>backend/services/__init__.py
tests/test_worker_runtime_boot.py</files>
  <read_first>.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
backend/services/__init__.py
backend/worker/__main__.py
backend/worker/loop.py
backend/observability/metrics.py
backend/services/recorded_chat_completion_service.py</read_first>
  <behavior>
    - Importing `backend.services.analysis_run_service` must no longer execute the heavy pipeline/LLM service graph at package import time.
    - `python -m backend.worker` must be importable without raising the current partially-initialized `observe_llm_completion` error.
    - The fix must preserve the current direct-module import style already used throughout the repo instead of introducing a second service-loading pattern.
  </behavior>
  <action>Rewrite `backend/services/__init__.py` so it no longer eagerly imports `EdgarPipelineExecutionService` or `EvaluationControlPlaneService` at module import time. Keep only the lightweight re-exports that are safe at package import time — `AnalysisRunService`, `ArtifactService`, `RunStepService`, `ToolCallService`, and `InvalidStatusTransition` — or replace the file with an equally light namespace surface that does not import the pipeline or evaluation-control-plane modules. Create `tests/test_worker_runtime_boot.py` that imports `backend.worker.__main__`, `backend.worker.loop`, and `backend.observability.metrics` in one test module and asserts those imports succeed without raising `ImportError` or a partially initialized module error. The new test should also assert `backend.worker.__main__.main` is callable so the worker entrypoint is locked as an import-safe surface.</action>
  <acceptance_criteria>`backend/services/__init__.py` does not contain `EdgarPipelineExecutionService`.
`backend/services/__init__.py` does not contain `EvaluationControlPlaneService`.
`backend/services/__init__.py` contains `AnalysisRunService`.
`backend/services/__init__.py` contains `ArtifactService`.
`tests/test_worker_runtime_boot.py` exists.
`tests/test_worker_runtime_boot.py` contains `import backend.worker.__main__`.
`tests/test_worker_runtime_boot.py` contains `import backend.worker.loop`.
`tests/test_worker_runtime_boot.py` contains `import backend.observability.metrics`.
`tests/test_worker_runtime_boot.py` contains `callable(`.
`python3 -m pytest tests/test_worker_runtime_boot.py tests/test_worker_lease_heartbeat.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_worker_runtime_boot.py tests/test_worker_lease_heartbeat.py -q --tb=short</automated>
  </verify>
  <done>The worker boot path is import-safe again, and the circular-import failure has a focused regression test.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Lock the documented stack smoke around synchronous and queued run execution</name>
  <files>scripts/smoke-compose.sh
tests/test_async_run_queue.py
tests/test_worker_job_lifecycle.py</files>
  <read_first>.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-RESEARCH.md
.planning/phases/12-runtime-reliability-for-chat-delivery/12-VALIDATION.md
scripts/smoke-compose.sh
docker-entrypoint.sh
backend/api/routes/runs.py
backend/services/run_queue_service.py
backend/worker/loop.py
tests/test_async_run_queue.py
tests/test_worker_job_lifecycle.py</read_first>
  <behavior>
    - The compose smoke path must verify both a synchronous run and a queued run instead of stopping at container health and login.
    - The queued path must prove a worker can claim work and move a run out of the initial queued or pending state in the documented stack.
    - The smoke and test coverage must fail loudly on the run-workspace permission class of error instead of letting it hide behind generic run failure.
  </behavior>
  <action>Extend `scripts/smoke-compose.sh` after the authenticated project-list step so it creates or reuses one project, then posts one synchronous run through `POST /v1/runs` followed by `POST /v1/runs/{run_id}/execute`, and posts one queued run through `POST /v1/runs` with `enqueue_execution=true`. Poll `GET /v1/runs/{run_id}/status` for the queued run until it no longer reports an open pending/running job in the initial state or until `SMOKE_WORKER_TIMEOUT` expires. Make the script fail if any run detail or status body includes `Permission denied`, if the synchronous run lands in `error`, or if the queued run never leaves the initial queued/pending state. Extend `tests/test_async_run_queue.py` and `tests/test_worker_job_lifecycle.py` so they explicitly lock the canonical queue claim and terminal transition behavior that the smoke script now depends on, including the case where a queued run transitions off `pending` after worker claim.</action>
  <acceptance_criteria>`scripts/smoke-compose.sh` contains `POST /v1/runs`.
`scripts/smoke-compose.sh` contains `/v1/runs/{run_id}/execute` or `"/execute"`.
`scripts/smoke-compose.sh` contains `enqueue_execution`.
`scripts/smoke-compose.sh` contains `SMOKE_WORKER_TIMEOUT`.
`scripts/smoke-compose.sh` contains `Permission denied`.
`scripts/smoke-compose.sh` contains `/status`.
`tests/test_async_run_queue.py` contains `AnalysisRunStatus.queued` or `"queued"`.
`tests/test_worker_job_lifecycle.py` contains `RunExecutionJobStatus.running` or `RunExecutionJobStatus.completed`.
`bash -n scripts/smoke-compose.sh` succeeds.
`python3 -m pytest tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>bash -n scripts/smoke-compose.sh && python3 -m pytest tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short</automated>
  </verify>
  <done>The documented stack smoke now covers the runtime seams Phase 12 must keep working: sync execution, worker-claimed queued execution, and run-workspace stability.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_worker_runtime_boot.py tests/test_worker_lease_heartbeat.py -q --tb=short` after the import-boundary repair, then rerun `bash -n scripts/smoke-compose.sh && python3 -m pytest tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short` once the stack smoke contract is updated.
</verification>

<success_criteria>
Phase 12 has a sound runtime foundation once the worker can boot without the current import cycle and the documented stack smoke proves both synchronous and queued execution survive the local run-workspace/runtime setup path.
</success_criteria>

<output>
After completion, create `.planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-01-SUMMARY.md`
</output>
