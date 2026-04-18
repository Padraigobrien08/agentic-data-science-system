---
phase: 10-live-hybrid-execution-hardening
plan: 03
type: execute
wave: 3
depends_on:
  - "10-02"
files_modified:
  - backend/api/routes/health.py
  - backend/schemas/health.py
  - backend/observability/metrics.py
  - backend/observability/evaluation_validation.py
  - tests/test_backend_health.py
  - tests/test_evaluation_live_hybrid_execution.py
  - README.md
autonomous: true
requirements:
  - EVAL-02
  - OPS-01
must_haves:
  truths:
    - "Health and metrics surfaces expose evaluation-specific SEC and storage degradation explicitly instead of showing false-green or empty state."
    - "Evaluation dependency observability is DB-backed and follows the same degraded-vs-unknown semantics as existing worker queue observability."
    - "Operators have a documented path from a degraded evaluation signal to the linked child run and existing artifact or trace surfaces."
  artifacts:
    - path: backend/observability/evaluation_validation.py
      provides: "DB-backed observability contract for recent evaluation SEC or storage degradation"
    - path: backend/api/routes/health.py
      provides: "JSON health responses with explicit evaluation dependency status"
    - path: backend/observability/metrics.py
      provides: "Prometheus gauges for evaluation dependency truthfulness"
    - path: tests/test_backend_health.py
      provides: "Regression coverage for health and metrics degraded-state reporting"
  key_links:
    - from: backend/api/routes/health.py
      to: backend/observability/evaluation_validation.py
      via: "JSON health routes expose evaluation dependency state from one DB-backed helper"
      pattern: "get_evaluation_validation_observability|EvaluationDependencyHealth"
    - from: backend/observability/metrics.py
      to: backend/observability/evaluation_validation.py
      via: "Prometheus gauges reuse the same evaluation observability contract as JSON health"
      pattern: "edgar_evaluation_dependency_observability_up|edgar_evaluation_sec_dependency_up|edgar_evaluation_storage_dependency_up"
    - from: README.md
      to: backend/api/routes/evaluations.py
      via: "docs tell operators how to move from a degraded evaluation case to the linked child run"
      pattern: "latest_analysis_run_id|/v1/evaluations|/v1/runs/{run_id}"
---

<objective>
Add truthful evaluation dependency observability to the existing JSON and Prometheus health surfaces and document the operator path from degraded evaluation signals to canonical child runs.

Purpose: satisfy the ops half of Phase 10 once canonical child-run execution is already in place.
Output: DB-backed evaluation dependency helper, extended health and metrics contracts, and focused degraded-state regressions.
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
@.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
@.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
@.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
@.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-PLAN.md
@backend/api/routes/health.py
@backend/schemas/health.py
@backend/observability/metrics.py
@backend/observability/worker_queue.py
@tests/test_backend_health.py

<interfaces>
From `backend/schemas/health.py`:
```python
class HealthResponse(BaseModel):
    status: str
    version: str
    database: DatabaseHealth
    llm: LlmHealth
```

From `backend/observability/metrics.py`:
```python
def refresh_worker_queue_gauges_from_db(session: Session, *, max_attempts: int) -> None: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add DB-backed evaluation dependency observability and expose it on JSON health routes</name>
  <files>backend/observability/evaluation_validation.py
backend/api/routes/health.py
backend/schemas/health.py
tests/test_backend_health.py
tests/test_evaluation_live_hybrid_execution.py</files>
  <read_first>.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-PLAN.md
backend/api/routes/health.py
backend/schemas/health.py
backend/observability/worker_queue.py
tests/test_backend_health.py
tests/test_evaluation_live_hybrid_execution.py</read_first>
  <behavior>
    - `/health` and `/v1/worker/health` expose an explicit evaluation dependency slice instead of making operators infer SEC or storage degradation from case messages.
    - Failed evaluation observability reads degrade the JSON health responses instead of silently returning healthy defaults.
    - The observability helper distinguishes SEC degradation from storage degradation and preserves a recent degraded-case count or equivalent operator breadcrumb.
  </behavior>
  <action>Create `backend/observability/evaluation_validation.py` with a dataclass such as `EvaluationValidationObservabilityResult` and a helper `get_evaluation_validation_observability(session: Session, *, lookback_hours: int = 24) -> EvaluationValidationObservabilityResult`. The helper must inspect recent `EvaluationCaseResult` rows, their `latest_analysis_run_id` links, and stored `metadata_json` error codes to compute `state_known`, `sec_dependency_ok`, `storage_dependency_ok`, `recent_degraded_case_count`, and a `detail` string when degraded or unknown. Add a new schema `EvaluationDependencyHealth` to `backend/schemas/health.py` with fields `state_known`, `sec_dependency_ok`, `storage_dependency_ok`, `recent_degraded_case_count`, and `detail`, then embed it on both `HealthResponse` and `WorkerHealthResponse` as `evaluation`. Update `backend/api/routes/health.py` so both `/health` and `/v1/worker/health` call the helper and set their top-level `status` to `degraded` whenever the evaluation helper reports unknown state or a false dependency boolean, even if the database query itself succeeded. Extend `tests/test_backend_health.py` and `tests/test_evaluation_live_hybrid_execution.py` to cover recent `upstream_sec_degraded` and storage-degraded linked cases, plus the degraded JSON response when the evaluation observability read itself raises a `SQLAlchemyError`.</action>
  <acceptance_criteria>`backend/observability/evaluation_validation.py` exists.
`backend/observability/evaluation_validation.py` contains `EvaluationValidationObservabilityResult`.
`backend/observability/evaluation_validation.py` contains `get_evaluation_validation_observability`.
`backend/schemas/health.py` contains `class EvaluationDependencyHealth`.
`backend/schemas/health.py` contains `recent_degraded_case_count`.
`backend/api/routes/health.py` contains `evaluation=`.
`backend/api/routes/health.py` contains `get_evaluation_validation_observability`.
`tests/test_backend_health.py` contains `recent_degraded_case_count`.
`tests/test_backend_health.py` contains `upstream_sec_degraded`.
`tests/test_backend_health.py` contains `storage_dependency_ok`.
`tests/test_evaluation_live_hybrid_execution.py` contains `artifact_storage_unavailable`.
`python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py -q --tb=short</automated>
  </verify>
  <done>JSON health surfaces now report evaluation SEC and storage degradation explicitly and degrade when the observability read itself fails.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Export truthful Prometheus gauges and document operator follow-through</name>
  <files>backend/observability/metrics.py
tests/test_backend_health.py
tests/test_evaluation_live_hybrid_execution.py
README.md</files>
  <read_first>.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
backend/observability/metrics.py
backend/observability/evaluation_validation.py
tests/test_backend_health.py
README.md</read_first>
  <behavior>
    - Prometheus scrapes expose evaluation dependency truth with explicit healthy, degraded, or unknown semantics.
    - Metric names stay app-owned and narrow to Phase 10’s evaluation SEC or storage degradation contract.
    - Operator docs explain how to move from a degraded evaluation signal to the linked child run and existing run trace surfaces.
  </behavior>
  <action>Update `backend/observability/metrics.py` to add the exact gauges `edgar_evaluation_dependency_observability_up`, `edgar_evaluation_sec_dependency_up`, `edgar_evaluation_storage_dependency_up`, and `edgar_evaluation_recent_degraded_cases`. Add a refresh helper that calls `get_evaluation_validation_observability(...)` during `/metrics` scrapes and sets those gauges to `1`, `0`, or `NaN` in the same style used by `refresh_worker_queue_gauges_from_db(...)`. When the evaluation observability read fails, set `edgar_evaluation_dependency_observability_up` to `0` and the two dependency gauges to `NaN`. Extend `tests/test_backend_health.py` so it asserts the new metric names exist and flip appropriately for healthy, SEC-degraded, storage-degraded, and observability-failed cases. Extend `tests/test_evaluation_live_hybrid_execution.py` if needed so the observability fixtures match the linked child-run metadata contract. Update `README.md` with a short operator section that says supported live or hybrid evaluations expose `latest_analysis_run_id` on case results, and that degraded health or metrics should be followed by inspecting the linked run through `/v1/runs/{run_id}` and the existing trace or artifact routes.</action>
  <acceptance_criteria>`backend/observability/metrics.py` contains `edgar_evaluation_dependency_observability_up`.
`backend/observability/metrics.py` contains `edgar_evaluation_sec_dependency_up`.
`backend/observability/metrics.py` contains `edgar_evaluation_storage_dependency_up`.
`backend/observability/metrics.py` contains `edgar_evaluation_recent_degraded_cases`.
`backend/observability/metrics.py` contains `get_evaluation_validation_observability`.
`tests/test_backend_health.py` contains `edgar_evaluation_sec_dependency_up`.
`tests/test_backend_health.py` contains `edgar_evaluation_storage_dependency_up`.
`tests/test_backend_health.py` contains `edgar_evaluation_dependency_observability_up`.
`README.md` contains `latest_analysis_run_id`.
`README.md` contains `/v1/runs/{run_id}`.
`README.md` contains `degraded`.
`python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py -q --tb=short</automated>
  </verify>
  <done>Prometheus and operator docs now expose the same evaluation dependency truth as the JSON health routes.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_backend_health.py tests/test_evaluation_live_hybrid_execution.py -q --tb=short` after each task so evaluation dependency observability stays truthful across JSON and Prometheus surfaces.
</verification>

<success_criteria>
Phase 10 is fully planned once evaluation SEC and storage degradation are explicit in health and metrics and operators know how to follow those signals into the linked child run audit trail.
</success_criteria>

<output>
After completion, create `.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md`
</output>
