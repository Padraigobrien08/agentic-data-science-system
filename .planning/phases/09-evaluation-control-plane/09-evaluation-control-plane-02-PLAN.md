---
phase: 09-evaluation-control-plane
plan: 02
type: execute
wave: 2
depends_on:
  - "09-01"
files_modified:
  - backend/repositories/evaluation_run_repository.py
  - backend/repositories/evaluation_case_result_repository.py
  - backend/services/evaluation_control_plane_service.py
  - backend/services/__init__.py
  - backend/api/deps.py
  - backend/api/routes/evaluations.py
  - backend/schemas/evaluation_run.py
  - edgar_project/evaluation/runner.py
  - tests/test_evaluation_control_plane_service.py
  - tests/test_evaluation_control_plane_api.py
autonomous: true
requirements:
  - VALID-01
  - EVAL-01
must_haves:
  truths:
    - "A supported evaluation run can be started through the API and persisted through `pending`, `running`, and terminal lifecycle states."
    - "Per-case rows store `input_mode`, `status`, `degradation_class`, `policy_json`, and `observation_json` derived from the existing runner output."
    - "Live and hybrid suites remain Phase 06-safe: explicit opt-in is carried into the persisted workflow, and policy-skipped or not-yet-implemented outcomes are still stored as first-class case records."
  artifacts:
    - path: backend/services/evaluation_control_plane_service.py
      provides: "Shared execution service that resolves suites, runs the evaluation runner, and persists aggregate plus case-level outcomes"
    - path: backend/api/routes/evaluations.py
      provides: "API start route for persisted supported evaluation runs"
    - path: tests/test_evaluation_control_plane_service.py
      provides: "Service regressions for lifecycle state, case-result persistence, and policy/observation storage"
    - path: tests/test_evaluation_control_plane_api.py
      provides: "API regressions for starting fixture, live, and hybrid evaluation runs"
  key_links:
    - from: backend/services/evaluation_control_plane_service.py
      to: edgar_project/evaluation/runner.py
      via: "the control-plane service persists the existing evaluation runner outputs instead of inventing a second execution engine"
      pattern: "EvaluationRunner|allow_live_cases|run_suite"
    - from: backend/api/routes/evaluations.py
      to: backend/services/evaluation_control_plane_service.py
      via: "the start route transitions a stored evaluation run through the shared execution service"
      pattern: "start_evaluation_run|allow_live"
    - from: tests/test_evaluation_control_plane_service.py
      to: backend/services/evaluation_control_plane_service.py
      via: "tests lock lifecycle transitions and stored per-case metadata for fixture, live, and hybrid starts"
      pattern: "policy_json|observation_json|degradation_class"
---

<objective>
Add the shared execution service and API start flow that turn persisted evaluation rows into persisted suite results.

Purpose: satisfy the execution half of Phase 09 by persisting runner outputs into first-class project-scoped resources.
Output: repositories, execution service, start request schema, and API regressions for fixture/live/hybrid persisted starts.
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
@.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
@.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
@.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
@.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-PLAN.md
@backend/models/evaluation_run.py
@backend/models/evaluation_case_result.py
@backend/api/routes/evaluations.py
@backend/services/artifact_service.py
@edgar_project/evaluation/catalog.py
@edgar_project/evaluation/runner.py
@edgar_project/evaluation/summary_report.py

<interfaces>
From `edgar_project/evaluation/runner.py`:
```python
class EvaluationRunner:
    def __init__(
        self,
        suite: BenchmarkSuite,
        rubric: Rubric | None = None,
        *,
        allow_live_cases: bool = False,
        update_regression_goldens: bool = False,
    ) -> None: ...
```

From `backend/models/evaluation_run.py`:
```python
class EvaluationRun(Base):
    status: Mapped[EvaluationRunStatus]
    started_at: Mapped[datetime | None]
    finished_at: Mapped[datetime | None]
    summary_json: Mapped[dict | list | None]
    results_json: Mapped[dict | list | None]
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add repositories and a shared control-plane execution service</name>
  <files>backend/repositories/evaluation_run_repository.py
backend/repositories/evaluation_case_result_repository.py
backend/services/evaluation_control_plane_service.py
backend/services/__init__.py
backend/api/deps.py
tests/test_evaluation_control_plane_service.py</files>
  <read_first>.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-PLAN.md
backend/models/evaluation_run.py
backend/models/evaluation_case_result.py
backend/services/run_lifecycle_service.py
backend/services/artifact_service.py
edgar_project/evaluation/catalog.py
edgar_project/evaluation/runner.py
edgar_project/evaluation/summary_report.py</read_first>
  <behavior>
    - A persisted evaluation row can be transitioned from `pending` to `running` to a terminal state through one shared service.
    - The service stores first-class case rows and keeps `summary_json` / `results_json` as backward-compatible aggregate exports.
    - Live and hybrid mode policy, observation, and degradation metadata are persisted even when Phase 09 still routes them to policy-skipped or not-yet-implemented outcomes.
  </behavior>
  <action>Create `backend/repositories/evaluation_run_repository.py` and `backend/repositories/evaluation_case_result_repository.py` with helpers to get one run for update, list runs by project, replace case results for a run, and count case rows. Add `backend/services/evaluation_control_plane_service.py` with a shared service class that accepts a SQLAlchemy session plus the suite catalog and exposes `start_evaluation_run(evaluation_run_id: UUID, *, allow_live: bool = False)`. The service must load the stored `EvaluationRun`, resolve its suite from the curated catalog, mark `status=running` with `started_at`, execute `EvaluationRunner(... allow_live_cases=allow_live)`, persist `summary_json`, persist a backward-compatible `results_json` export, replace `evaluation_case_results` rows with the exact fields `case_id`, `input_mode`, `status`, `degradation_class`, `run_goal`, `message`, `policy_json`, `observation_json`, `checks_json`, `metadata_json`, and `artifacts_json`, then mark terminal `passed`, `failed`, `skipped`, or `error` with `finished_at`. Export the service from `backend/services/__init__.py` and add a dependency alias in `backend/api/deps.py`. Seed `tests/test_evaluation_control_plane_service.py` with service-level tests for fixture success, live policy-skipped without opt-in, and stored policy/observation JSON on live or hybrid cases.</action>
  <acceptance_criteria>`backend/repositories/evaluation_run_repository.py` exists.
`backend/repositories/evaluation_case_result_repository.py` exists.
`backend/services/evaluation_control_plane_service.py` exists.
`backend/services/evaluation_control_plane_service.py` contains `start_evaluation_run`.
`backend/services/evaluation_control_plane_service.py` contains `EvaluationRunner(`.
`backend/services/evaluation_control_plane_service.py` contains `allow_live_cases=allow_live`.
`backend/services/evaluation_control_plane_service.py` assigns `started_at`.
`backend/services/evaluation_control_plane_service.py` assigns `finished_at`.
`backend/services/evaluation_control_plane_service.py` writes `policy_json`.
`backend/services/evaluation_control_plane_service.py` writes `observation_json`.
`tests/test_evaluation_control_plane_service.py` exists.
`tests/test_evaluation_control_plane_service.py` contains `policy_skipped`.
`tests/test_evaluation_control_plane_service.py` contains `observation_json`.
`python3 -m pytest tests/test_evaluation_control_plane_service.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_control_plane_service.py -q --tb=short</automated>
  </verify>
  <done>The backend now has one shared execution service that persists supported evaluation outcomes into first-class rows.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Expose an API-backed start route for persisted fixture, live, and hybrid workflows</name>
  <files>backend/api/routes/evaluations.py
backend/schemas/evaluation_run.py
edgar_project/evaluation/runner.py
tests/test_evaluation_control_plane_api.py
tests/test_evaluation_control_plane_service.py</files>
  <read_first>.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-PLAN.md
backend/api/routes/evaluations.py
backend/schemas/evaluation_run.py
backend/services/evaluation_control_plane_service.py
edgar_project/evaluation/runner.py
tests/test_evaluation_control_plane_api.py
tests/test_evaluation_control_plane_service.py</read_first>
  <behavior>
    - Operators can start a stored evaluation run through the API without bypassing the project-scoped persisted record.
    - The start request carries the same explicit live opt-in concept as the Phase 06 CLI contract.
    - Fixture, live, and hybrid suite starts all produce persisted case-result rows even when live or hybrid execution remains policy-skipped or not-yet-implemented in this phase.
  </behavior>
  <action>Add `EvaluationRunStartRequest` to `backend/schemas/evaluation_run.py` with the exact field `allow_live: bool = False`. Extend `backend/api/routes/evaluations.py` with `@router.post("/{evaluation_run_id}/start"` that requires ownership via `require_evaluation_run_owned`, rejects non-`pending` rows with `409`, calls `EvaluationControlPlaneService.start_evaluation_run(...)`, refreshes the row, and returns the updated read model with a populated `case_count`. Ensure `edgar_project/evaluation/runner.py` still treats `allow_live_cases=False` as `policy_skipped` for live and hybrid suites and preserves policy/observation fields in the emitted `EvaluationResult` records. Extend `tests/test_evaluation_control_plane_api.py` so it covers starting `suite_fixtures_v1`, starting `suite_smoke` without `allow_live` and observing persisted `policy_skipped`, and starting `suite_hybrid_smoke_v1` with `allow_live=true` while still persisting the case row and policy metadata. Extend `tests/test_evaluation_control_plane_service.py` as needed so both API and service expectations agree on terminal statuses and case counts.</action>
  <acceptance_criteria>`backend/schemas/evaluation_run.py` contains `class EvaluationRunStartRequest`.
`backend/schemas/evaluation_run.py` contains `allow_live: bool = False`.
`backend/api/routes/evaluations.py` contains `@router.post("/{evaluation_run_id}/start"`.
`backend/api/routes/evaluations.py` contains `require_evaluation_run_owned`.
`backend/api/routes/evaluations.py` contains `start_evaluation_run`.
`backend/api/routes/evaluations.py` returns `409` for non-pending evaluation runs.
`tests/test_evaluation_control_plane_api.py` contains `/v1/evaluations/` and `/start`.
`tests/test_evaluation_control_plane_api.py` contains `policy_skipped`.
`tests/test_evaluation_control_plane_api.py` contains `suite_hybrid_smoke_v1`.
`tests/test_evaluation_control_plane_api.py` asserts persisted case rows exist after starting fixture, live, and hybrid suites.
`python3 -m pytest tests/test_evaluation_control_plane_service.py tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_control_plane_service.py tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>Operators can now start supported evaluation runs through the API and receive persisted lifecycle and case-level outcomes.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_control_plane_service.py tests/test_evaluation_control_plane_api.py -q --tb=short` after each task so the shared service and API start route stay aligned.
</verification>

<success_criteria>
Phase 09 satisfies the execution requirement once a supported evaluation run can be started through the API and persisted as both an aggregate evaluation row and first-class case-result records.
</success_criteria>

<output>
After completion, create `.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md`
</output>
