---
phase: 10-live-hybrid-execution-hardening
plan: 02
type: execute
wave: 2
depends_on:
  - "10-01"
files_modified:
  - backend/services/evaluation_control_plane_service.py
  - backend/api/routes/evaluations.py
  - backend/schemas/evaluation_run.py
  - backend/schemas/evaluation_case_result.py
  - edgar_project/evaluation/runner.py
  - tests/test_evaluation_live_hybrid_execution.py
  - tests/test_evaluation_control_plane_api.py
autonomous: true
requirements:
  - EVAL-02
must_haves:
  truths:
    - "Starting a live or hybrid supported evaluation enqueues canonical child runs and returns immediately with the evaluation aggregate still in a truthful running state."
    - "Evaluation case and aggregate verdicts are reconciled from linked `AnalysisRun` truth plus the existing degradation taxonomy, not from an opaque execution log."
    - "Operators can move from an evaluation case result to its latest linked run through the existing run APIs."
  artifacts:
    - path: backend/services/evaluation_control_plane_service.py
      provides: "Async launch and reconciliation logic for live or hybrid child-run-backed evaluation cases"
    - path: backend/api/routes/evaluations.py
      provides: "Evaluation routes that refresh linked child-run state before returning case or aggregate views"
    - path: tests/test_evaluation_live_hybrid_execution.py
      provides: "Regression coverage for queued launch, case reconciliation, and aggregate evaluation state transitions"
  key_links:
    - from: backend/api/routes/evaluations.py
      to: backend/services/evaluation_control_plane_service.py
      via: "evaluation detail and case routes refresh linked child-run state before serializing responses"
      pattern: "refresh_linked_case_results|latest_analysis_run_id|EvaluationStatus.pending"
    - from: backend/services/evaluation_control_plane_service.py
      to: edgar_project/evaluation/runner.py
      via: "the control plane reuses the existing degradation taxonomy helper instead of inventing a second classification contract"
      pattern: "classify_degradation_class_for_case|ValidationDegradationClass|EvaluationResult"
    - from: tests/test_evaluation_live_hybrid_execution.py
      to: backend/services/evaluation_control_plane_service.py
      via: "tests lock terminal case verdicts to linked child-run status and degradation evidence"
      pattern: "AnalysisRunStatus.success|AnalysisRunStatus.error|upstream_error_code|storage_error_code"
---

<objective>
Convert live and hybrid supported evaluation starts into queue-backed child-run launches and reconcile case plus aggregate verdicts from linked canonical runs.

Purpose: satisfy the execution half of Phase 10 by making canonical runs the only runtime source of truth for live or hybrid validation.
Output: async start flow, linked-run refresh logic, and API regressions for case-to-run navigation and terminal verdict reconciliation.
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
@.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-PLAN.md
@backend/services/evaluation_control_plane_service.py
@backend/api/routes/evaluations.py
@backend/schemas/evaluation_case_result.py
@backend/schemas/evaluation_run.py
@edgar_project/evaluation/runner.py
@backend/models/enums.py

<interfaces>
From `edgar_project/evaluation/schemas.py`:
```python
class EvaluationStatus(str, Enum):
    pending = "pending"
    passed = "passed"
    failed = "failed"
    skipped = "skipped"
    error = "error"
```

From `backend/models/enums.py`:
```python
class AnalysisRunStatus(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    success = "success"
    error = "error"
    cancelled = "cancelled"
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make live and hybrid evaluation starts enqueue child runs and return immediately</name>
  <files>backend/services/evaluation_control_plane_service.py
backend/api/routes/evaluations.py
backend/schemas/evaluation_run.py
tests/test_evaluation_live_hybrid_execution.py
tests/test_evaluation_control_plane_api.py</files>
  <read_first>.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-PLAN.md
backend/services/evaluation_control_plane_service.py
backend/api/routes/evaluations.py
backend/schemas/evaluation_run.py
edgar_project/evaluation/catalog.py
edgar_project/evaluation/schemas.py
tests/test_evaluation_live_hybrid_execution.py</read_first>
  <behavior>
    - Live and hybrid supported evaluation starts return with the evaluation aggregate in `running`, not after inline suite execution completes.
    - Pure fixture or `orchestration_mocked` suites keep the existing Phase 09 synchronous behavior.
    - Live and hybrid case rows are created as `pending` with policy and observation context preserved before the child runs are queued.
  </behavior>
  <action>Update `backend/services/evaluation_control_plane_service.py` so `start_evaluation_run(...)` branches by case mode. For suites containing `InputMode.live` or `InputMode.hybrid`, create or upsert one `EvaluationCaseResult` row per case with `status=EvaluationStatus.pending.value`, `degradation_class=ValidationDegradationClass.none.value`, `policy_json` copied from `case.input.policy.model_dump(mode="json")`, and `observation_json` seeded with at least `freshness_window_seconds`. Call `_enqueue_live_or_hybrid_case_run(...)` for each live or hybrid case, set `EvaluationRun.status = EvaluationRunStatus.running`, set `started_at`, clear `finished_at`, and return without calling `EvaluationRunner.run_suite()` for those cases. Keep the existing synchronous runner path for suites whose cases are all `fixture` or `orchestration_mocked`. Update `backend/api/routes/evaluations.py` so `POST /v1/evaluations/{evaluation_run_id}/start` still returns the refreshed `EvaluationRunRead` payload, but now tolerates a `running` aggregate with pending child-backed cases. Extend `tests/test_evaluation_live_hybrid_execution.py` and `tests/test_evaluation_control_plane_api.py` so starting `suite_smoke` and `suite_hybrid_smoke_v1` yields `status == "running"`, pending case rows, and non-null `latest_analysis_run_id` values, while `suite_fixtures_v1` keeps the synchronous terminal behavior from Phase 09.</action>
  <acceptance_criteria>`backend/services/evaluation_control_plane_service.py` contains `InputMode.live`.
`backend/services/evaluation_control_plane_service.py` contains `InputMode.hybrid`.
`backend/services/evaluation_control_plane_service.py` assigns `EvaluationRunStatus.running`.
`backend/services/evaluation_control_plane_service.py` assigns `EvaluationStatus.pending`.
`backend/services/evaluation_control_plane_service.py` contains `ValidationDegradationClass.none`.
`backend/services/evaluation_control_plane_service.py` contains `policy_json`.
`backend/services/evaluation_control_plane_service.py` contains `observation_json`.
`backend/api/routes/evaluations.py` contains `@router.post("/{evaluation_run_id}/start"`.
`tests/test_evaluation_live_hybrid_execution.py` contains `suite_smoke`.
`tests/test_evaluation_live_hybrid_execution.py` contains `suite_hybrid_smoke_v1`.
`tests/test_evaluation_live_hybrid_execution.py` asserts `status == "running"`.
`tests/test_evaluation_control_plane_api.py` contains `latest_analysis_run_id`.
`python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>Live and hybrid supported evaluation starts are now asynchronous child-run launches instead of inline runner calls.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Reconcile case and aggregate verdicts from linked child-run truth</name>
  <files>backend/services/evaluation_control_plane_service.py
backend/api/routes/evaluations.py
backend/schemas/evaluation_case_result.py
backend/schemas/evaluation_run.py
edgar_project/evaluation/runner.py
tests/test_evaluation_live_hybrid_execution.py
tests/test_evaluation_control_plane_api.py</files>
  <read_first>.planning/phases/10-live-hybrid-execution-hardening/10-CONTEXT.md
.planning/phases/10-live-hybrid-execution-hardening/10-RESEARCH.md
.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md
.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-PLAN.md
backend/services/evaluation_control_plane_service.py
backend/api/routes/evaluations.py
backend/schemas/evaluation_case_result.py
backend/schemas/evaluation_run.py
edgar_project/evaluation/runner.py
backend/models/enums.py
tests/test_evaluation_live_hybrid_execution.py</read_first>
  <behavior>
    - Non-terminal linked child runs keep the case in `EvaluationStatus.pending` without inventing a new lifecycle.
    - Terminal linked child runs update the case status, degradation class, message, and aggregate evaluation summary from canonical run truth.
    - Evaluation APIs refresh linked-run state before returning so operators can navigate directly to the latest child run from any case view.
  </behavior>
  <action>Expose a reusable pure helper in `edgar_project/evaluation/runner.py` named `classify_degradation_class_for_case(case: BenchmarkCase, result: EvaluationResult, *, allow_live_cases: bool) -> ValidationDegradationClass` by lifting the existing `_classify_degradation_class` logic into a callable the control plane can import. Then update `backend/services/evaluation_control_plane_service.py` to add a refresh method such as `refresh_linked_case_results(evaluation_run_id: UUID) -> EvaluationRun`. That method must load linked case rows and their `latest_analysis_run_id` targets, map `AnalysisRunStatus.pending`, `queued`, and `running` to `EvaluationStatus.pending`, map `AnalysisRunStatus.success` to an `EvaluationResult(status=EvaluationStatus.passed, ...)`, and map `AnalysisRunStatus.error` or `cancelled` to `EvaluationResult(status=EvaluationStatus.error, ...)` or `failed` with `message` derived from `error_summary`. When child-run metadata or error text indicates SEC failure, write `metadata_json["upstream_error_code"]` with values such as `sec_rate_limited`, `sec_access_denied`, or `sec_unavailable`; when it indicates remote storage failure, write `metadata_json["storage_error_code"]` with a concrete code such as `artifact_storage_unavailable`. Feed that `EvaluationResult` plus the case definition into `classify_degradation_class_for_case(...)` and persist the resulting degradation class. Refresh `summary_json`, `results_json`, `case_count`, and `EvaluationRun.status` after reconciling all rows: stay `running` while any case is pending, otherwise compute terminal `passed`, `failed`, or `error` from the linked case rows. Update `backend/api/routes/evaluations.py` so `GET /v1/evaluations/{evaluation_run_id}`, `GET /v1/evaluations/{evaluation_run_id}/cases`, and `GET /v1/evaluations/{evaluation_run_id}/cases/{case_id}` call the refresh method before serializing responses. Extend `tests/test_evaluation_live_hybrid_execution.py` and `tests/test_evaluation_control_plane_api.py` so they cover pending child runs, successful child runs, SEC degradation, storage degradation, and direct case-to-run navigation through `latest_analysis_run_id`.</action>
  <acceptance_criteria>`edgar_project/evaluation/runner.py` contains `classify_degradation_class_for_case`.
`backend/services/evaluation_control_plane_service.py` contains `refresh_linked_case_results`.
`backend/services/evaluation_control_plane_service.py` contains `EvaluationStatus.pending`.
`backend/services/evaluation_control_plane_service.py` contains `AnalysisRunStatus.success`.
`backend/services/evaluation_control_plane_service.py` contains `AnalysisRunStatus.error`.
`backend/services/evaluation_control_plane_service.py` contains `upstream_error_code`.
`backend/services/evaluation_control_plane_service.py` contains `storage_error_code`.
`backend/services/evaluation_control_plane_service.py` contains `artifact_storage_unavailable`.
`backend/api/routes/evaluations.py` contains `refresh_linked_case_results`.
`tests/test_evaluation_live_hybrid_execution.py` contains `sec_rate_limited`.
`tests/test_evaluation_live_hybrid_execution.py` contains `artifact_storage_unavailable`.
`tests/test_evaluation_control_plane_api.py` contains `latest_analysis_run_id`.
`tests/test_evaluation_control_plane_api.py` asserts linked child runs can be reopened through the run APIs.
`python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>Live and hybrid evaluation verdicts now reconcile from canonical child-run truth, and case responses expose direct latest-run navigation.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short` after each task so asynchronous launch and run-backed reconciliation remain aligned.
</verification>

<success_criteria>
Phase 10 satisfies its core execution goal once live and hybrid evaluations start through the canonical queue path and every case verdict is derived from linked child-run state instead of a separate runtime lifecycle.
</success_criteria>

<output>
After completion, create `.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md`
</output>
