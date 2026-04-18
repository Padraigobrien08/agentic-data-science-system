---
phase: 09-evaluation-control-plane
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - edgar_project/evaluation/catalog.py
  - edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json
  - alembic/versions/012_evaluation_control_plane_case_results.py
  - backend/models/evaluation_case_result.py
  - backend/models/evaluation_run.py
  - backend/models/__init__.py
  - backend/schemas/evaluation_run.py
  - backend/schemas/evaluation_case_result.py
  - backend/schemas/__init__.py
  - backend/api/access_checks.py
  - backend/api/routes/evaluations.py
  - backend/api/router.py
  - tests/test_evaluation_control_plane_api.py
autonomous: true
requirements:
  - VALID-01
  - EVAL-01
must_haves:
  truths:
    - "Supported evaluation launches resolve explicit curated suite IDs instead of accepting arbitrary manifest paths as the product contract."
    - "Evaluation persistence gains a first-class case-result seam under `EvaluationRun` rather than relying only on `results_json` blobs."
    - "The backend exposes project-scoped evaluation suite, create, list, and detail routes before execution logic is layered on."
  artifacts:
    - path: edgar_project/evaluation/catalog.py
      provides: "Curated supported-suite registry for fixture, live, and hybrid evaluation workflows"
    - path: backend/models/evaluation_case_result.py
      provides: "First-class persisted per-case evaluation result resource"
    - path: backend/api/routes/evaluations.py
      provides: "Project-scoped API foundation for suite listing and persisted evaluation-run CRUD"
    - path: tests/test_evaluation_control_plane_api.py
      provides: "API regressions for curated suite IDs, project scoping, and pending evaluation-run creation"
  key_links:
    - from: backend/api/routes/evaluations.py
      to: edgar_project/evaluation/catalog.py
      via: "public create and suite-list routes resolve supported suite IDs through the curated catalog"
      pattern: "list_supported_evaluation_suites|get_supported_evaluation_suite|suite_id"
    - from: backend/models/evaluation_case_result.py
      to: backend/models/evaluation_run.py
      via: "evaluation runs own persisted child case results rather than storing only one opaque result blob"
      pattern: "evaluation_run_id|case_results"
    - from: tests/test_evaluation_control_plane_api.py
      to: backend/api/routes/evaluations.py
      via: "tests lock the project-scoped route contract and reject unknown or caller-supplied suite paths"
      pattern: "/v1/evaluations/suites|/v1/evaluations|suite_manifest_path"
---

<objective>
Add the supported-suite registry, first-class case-result persistence foundation, and the initial project-scoped evaluation API surface.

Purpose: establish the Phase 09 product contract before execution or CLI compatibility work begins.
Output: curated suite catalog, case-result model and migration, plus authenticated evaluation suite/create/list/detail routes.
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
@backend/models/evaluation_run.py
@backend/schemas/evaluation_run.py
@backend/auth/resource_access.py
@backend/api/access_checks.py
@backend/api/router.py
@edgar_project/evaluation/schemas.py
@edgar_project/evaluation/benchmarks/suite_fixtures_v1.json
@edgar_project/evaluation/benchmarks/suite_smoke.json

<interfaces>
From `backend/models/evaluation_run.py`:
```python
class EvaluationRun(Base):
    suite_id: Mapped[str]
    suite_manifest_path: Mapped[str | None]
    status: Mapped[EvaluationRunStatus]
    summary_json: Mapped[dict | list | None]
    results_json: Mapped[dict | list | None]
```

From `backend/schemas/evaluation_run.py`:
```python
class EvaluationRunCreate(OrmSchema):
    suite_id: str
    suite_manifest_path: str | None = None
    project_id: UUID | None = None
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add a curated supported-suite catalog and approved hybrid smoke scaffold</name>
  <files>edgar_project/evaluation/catalog.py
edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json
tests/test_evaluation_control_plane_api.py</files>
  <read_first>.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
edgar_project/evaluation/benchmarks/suite_fixtures_v1.json
edgar_project/evaluation/benchmarks/suite_smoke.json
edgar_project/evaluation/schemas.py</read_first>
  <behavior>
    - Supported evaluation launches use stable suite IDs backed by approved manifests instead of arbitrary caller-provided file paths.
    - The supported catalog includes one fixture suite, one live smoke suite, and one hybrid smoke suite so all required input modes can be started through the control plane.
    - The hybrid smoke suite follows the Phase 06 live-policy rules and remains a scaffold for Phase 09 persistence, not a child-run execution implementation.
  </behavior>
  <action>Create `edgar_project/evaluation/catalog.py` with a typed registry object such as `SupportedEvaluationSuite` plus exported helpers `list_supported_evaluation_suites()` and `get_supported_evaluation_suite(suite_id: str)`. The registry must contain the exact supported IDs `suite_fixtures_v1`, `suite_smoke`, and `suite_hybrid_smoke_v1`, and each entry must define the resolved manifest path under `edgar_project/evaluation/benchmarks/`, an operator-facing label, and the suite's primary mode. Add `edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json` with one `hybrid` case that mirrors the live smoke policy scaffold: `requires_explicit_live_opt_in: true`, `fair_access_policy: "sec_fair_access_operator_invoked"`, `allow_merge_blocking: false`, `normal_user_visible: false`, and `freshness_window_seconds: 300`. Seed `tests/test_evaluation_control_plane_api.py` with catalog-level assertions that the supported suite list contains exactly those IDs and no arbitrary path input.</action>
  <acceptance_criteria>`edgar_project/evaluation/catalog.py` exists.
`edgar_project/evaluation/catalog.py` contains `list_supported_evaluation_suites`.
`edgar_project/evaluation/catalog.py` contains `get_supported_evaluation_suite`.
`edgar_project/evaluation/catalog.py` contains `suite_fixtures_v1`.
`edgar_project/evaluation/catalog.py` contains `suite_smoke`.
`edgar_project/evaluation/catalog.py` contains `suite_hybrid_smoke_v1`.
`edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json` exists.
`edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json` contains `"mode": "hybrid"`.
`edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json` contains `"requires_explicit_live_opt_in": true`.
`tests/test_evaluation_control_plane_api.py` contains `suite_hybrid_smoke_v1`.
`python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>The supported evaluation workflow now has an explicit catalog contract for fixture, live, and hybrid suite IDs.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add case-result persistence and project-scoped evaluation create/list/detail routes</name>
  <files>alembic/versions/012_evaluation_control_plane_case_results.py
backend/models/evaluation_case_result.py
backend/models/evaluation_run.py
backend/models/__init__.py
backend/schemas/evaluation_run.py
backend/schemas/evaluation_case_result.py
backend/schemas/__init__.py
backend/api/access_checks.py
backend/api/routes/evaluations.py
backend/api/router.py
tests/test_evaluation_control_plane_api.py</files>
  <read_first>.planning/phases/09-evaluation-control-plane/09-CONTEXT.md
.planning/phases/09-evaluation-control-plane/09-RESEARCH.md
.planning/phases/09-evaluation-control-plane/09-VALIDATION.md
backend/models/evaluation_run.py
backend/schemas/evaluation_run.py
backend/api/access_checks.py
backend/api/router.py
backend/api/routes/projects.py
backend/api/routes/runs.py
backend/auth/resource_access.py</read_first>
  <behavior>
    - `EvaluationRun` becomes the aggregate for first-class stored case results, not just summary/results blobs.
    - Public API create requests accept curated `suite_id` and `project_id`, but do not accept caller-supplied `suite_manifest_path`.
    - Evaluation routes follow the existing owner-project boundary and return `404` for non-owned projects or evaluation runs.
  </behavior>
  <action>Create `alembic/versions/012_evaluation_control_plane_case_results.py` that adds an `evaluation_case_results` table with a UUID primary key plus the exact columns `evaluation_run_id`, `case_id`, `input_mode`, `status`, `degradation_class`, `run_goal`, `message`, `policy_json`, `observation_json`, `checks_json`, `metadata_json`, `artifacts_json`, `created_at`, and `updated_at`, and enforce one unique row per `(evaluation_run_id, case_id)`. Add `backend/models/evaluation_case_result.py` with the matching SQLAlchemy model and a `case_results` relationship on `EvaluationRun`, then export it from `backend/models/__init__.py`. Add `backend/schemas/evaluation_case_result.py` with typed read models for stored case outcomes, and change `backend/schemas/evaluation_run.py` so the public create schema only accepts `project_id`, `suite_id`, `config_json`, and `notes` while the read schema includes `case_count: int | None = None`. Add `require_evaluation_run_owned(...)` to `backend/api/access_checks.py`. Create `backend/api/routes/evaluations.py` with `router = APIRouter(prefix="/evaluations", tags=["evaluations"])` and implement `GET /v1/evaluations/suites`, `GET /v1/evaluations`, `POST /v1/evaluations`, and `GET /v1/evaluations/{evaluation_run_id}`. `POST /v1/evaluations` must require project ownership, resolve `suite_manifest_path` from the catalog, set `status=pending`, and never accept or persist a caller-provided manifest path. Register the router in `backend/api/router.py`. Extend `tests/test_evaluation_control_plane_api.py` so it covers suite listing, pending create/list/detail behavior, unknown suite IDs returning `400`, and cross-project access returning `404`.</action>
  <acceptance_criteria>`backend/models/evaluation_case_result.py` exists.
`backend/models/evaluation_case_result.py` contains `class EvaluationCaseResult`.
`backend/models/evaluation_run.py` contains `case_results`.
`alembic/versions/012_evaluation_control_plane_case_results.py` exists.
`alembic/versions/012_evaluation_control_plane_case_results.py` contains `evaluation_case_results`.
`backend/schemas/evaluation_run.py` no longer exposes `suite_manifest_path` on the public create schema.
`backend/api/access_checks.py` contains `require_evaluation_run_owned`.
`backend/api/routes/evaluations.py` exists.
`backend/api/routes/evaluations.py` contains `@router.get("/suites"`.
`backend/api/routes/evaluations.py` contains `@router.post(""`.
`backend/api/router.py` contains `evaluations.router`.
`tests/test_evaluation_control_plane_api.py` contains `/v1/evaluations/suites`.
`tests/test_evaluation_control_plane_api.py` contains `/v1/evaluations`.
`tests/test_evaluation_control_plane_api.py` asserts unknown suite IDs return `400`.
`tests/test_evaluation_control_plane_api.py` asserts cross-project requests return `404`.
`python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short</automated>
  </verify>
  <done>The project now has a supported suite catalog, a first-class case-result persistence seam, and a project-scoped evaluation API foundation.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short` after each task so the new catalog and API foundation stay aligned.
</verification>

<success_criteria>
Phase 09 has a sound foundation once the backend exposes curated supported suites, stores case results as first-class rows, and lets owners create and inspect pending evaluation runs through the API.
</success_criteria>

<output>
After completion, create `.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md`
</output>
