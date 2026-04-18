# Phase 09: Evaluation Control Plane - Research

**Researched:** 2026-04-18
**Domain:** API-backed evaluation control plane with project-scoped persisted runs and case results
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The supported evaluation control plane should be API-backed first, with the CLI kept as a compatibility path rather than remaining the primary product workflow.
- **D-02:** Phase 9 should treat persisted evaluation runs as product resources that other surfaces can call, not as side effects of local-only scripts.
- **D-03:** Supported evaluation launches should use curated suite IDs or approved manifests, not arbitrary repo file paths supplied at runtime.
- **D-04:** The control plane should make suite identity explicit and auditable so a later operator can tell exactly which supported evaluation definition was run.
- **D-05:** Supported evaluation runs should be project-scoped by default.
- **D-06:** Evaluation ownership and visibility should follow the existing project-owner boundary instead of introducing a new global operator-only auth model in this phase.
- **D-07:** Operators should reopen an evaluation run into a persisted run summary plus explicit per-case results, not just one opaque `results_json` blob.
- **D-08:** Case-level outcomes should remain reviewable as first-class persisted records even if summary JSON views still exist for export or convenience.

### the agent's Discretion
- Exact service and API route shape for evaluation-run create/list/detail/start operations
- Exact persistence model for case results, as long as they are first-class persisted records rather than only an opaque blob
- Exact CLI compatibility path, as long as CLI usage no longer defines the only supported workflow
- Exact operator review surface, as long as evaluation history is project-scoped, auditable, and reopenable

### Deferred Ideas (OUT OF SCOPE)
- Child `AnalysisRun` linkage for live and hybrid validation cases
- Global cross-project operator console for evaluations
- Arbitrary file-path suite execution as a supported product surface
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| VALID-01 | Operator can start fixture, hybrid, and live evaluation runs through a supported workflow with mode-specific policy and persisted observation metadata | Add a supported suite catalog, API-backed launch flow, and a shared execution service that persists policy/observation fields from the existing evaluation runner. |
| EVAL-01 | Operator can manage supported evaluation runs and case results as first-class persisted records instead of ad hoc script output | Add project-scoped evaluation routes and a first-class case-result table so review and history no longer depend on `results_json` blobs alone. |
</phase_requirements>

## Summary

The repo already has half of a control plane, but only half. `backend/models/evaluation_run.py` gives the system a persisted aggregate with project ownership, artifacts, and model-call links, yet the actual supported workflow is still `python3 -m edgar_project.cli evaluate` reading a file path, running the suite locally, and writing `*_results.json` and `*_summary.json` beside the benchmark outputs. There is no evaluation API surface in `backend/api/router.py`, no evaluation repository or service layer, and no first-class case-result resource for operators to reopen later.

That makes Phase 09 mostly a persistence and product-surface problem, not a new evaluation-engine problem. The evaluation package already gives us the typed result contract we need: `edgar_project/evaluation/schemas.py` has input modes, policy, observation, and degradation classes; `edgar_project/evaluation/runner.py` already emits per-case `EvaluationResult` objects; and `summary_report.py` already knows how to derive aggregate suite summaries. The missing move is to persist those results as product data instead of leaving them trapped in one JSON blob or one local file-output session.

The lowest-risk brownfield design is therefore three additive layers. First, define a curated supported-suite catalog that resolves explicit suite IDs to approved manifests so the supported workflow stops depending on arbitrary repo paths. Second, add a project-scoped control-plane API and a first-class `EvaluationCaseResult` persistence seam under the existing `EvaluationRun` aggregate. Third, add one shared execution service that loads a supported suite, runs the existing runner, updates `EvaluationRun` lifecycle state, and persists per-case rows plus aggregate summary data. The API becomes the supported workflow, while the CLI becomes a compatibility surface that can call the same catalog and service when a project-scoped persisted run is desired.

**Primary recommendation:** keep Phase 09 execution synchronous and service-backed. Create the `EvaluationRun` first, mark it `running`, execute the existing `EvaluationRunner` in-process, persist `summary_json` plus explicit case-result rows, and return the terminal row through the API. That keeps the control plane API-backed right now without prematurely introducing a second queueing system or child `AnalysisRun` linkage, both of which belong in Phase 10.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or `.agents/skills/` directory exists under the project root.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| FastAPI route layer in `backend/api/routes/` | in-repo seam | Add authenticated evaluation list/create/detail/start/review endpoints | The backend already exposes project- and run-scoped product resources this way. |
| SQLAlchemy models + Alembic migrations | in-repo seam | Add first-class case-result persistence and any aggregate-field adjustments | The project already uses DB-backed lifecycle rows plus migrations for all durable product data. |
| Pydantic schemas in `backend/schemas/` | in-repo seam | Add wire contracts for supported suites, evaluation runs, start requests, and case results | This matches the existing API style for runs, artifacts, and projects. |
| Existing evaluation runner + summary contracts | in-repo seam | Produce the case-level policy/observation/degradation metadata that must be persisted | Phase 09 should not fork or reimplement the runner; it should persist its outputs. |
| `pytest 8.4.2` via `pytest.ini` | local repo tooling | API, service, and CLI compatibility regressions | Existing backend phases already rely on focused pytest contract tests. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `backend/auth/resource_access.py` + `backend/api/access_checks.py` | in-repo seam | Reuse project-owner authorization for evaluation history and evaluation artifacts | Use for consistent 404-on-non-owned behavior. |
| `backend/services/artifact_service.py` | in-repo seam | Preserve evaluation artifact ingestion under `evaluation_run_id` | Use if supported evaluation execution stores markdown or JSON report artifacts. |
| `edgar_project/evaluation/benchmarks/*.json` | in-repo seam | Back the curated supported-suite catalog with approved manifests | Use current fixture and live smoke manifests, plus a new approved hybrid smoke scaffold. |
| `edgar_project/cli.py` | in-repo seam | Keep a compatibility path that resolves supported suite IDs instead of only raw file paths | Use only after the API-backed persisted path exists. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Curated suite catalog with explicit IDs | Keep `--suite path.json` as the supported launch contract | Simpler for devs, but not auditable or safe enough for a product control plane. |
| `EvaluationRun` + `EvaluationCaseResult` rows | Keep only `summary_json` and `results_json` blobs | Faster to ship, but it violates the explicit “first-class case results” requirement. |
| API-backed synchronous execution in this phase | Build an evaluation queue or worker now | Better for scale later, but it widens scope into orchestration and lease behavior already solved elsewhere. |
| Project-scoped evaluation ownership | Introduce a new operator-global evaluation namespace | Adds an auth model the repo does not need for this phase. |
| CLI compatibility via catalog/service reuse | Let CLI remain a totally separate path-based implementation | Preserves drift between supported workflows and local tooling. |

## Architecture Patterns

### Pattern 1: Supported Suite Catalog as the Public Contract

**What:** Add a small catalog module that maps stable suite IDs to approved manifest paths plus operator-facing labels and mode metadata.

**When to use:** Every supported API or CLI launch path in this phase.

**Why:** Phase 09 is explicitly rejecting arbitrary file paths as the supported contract. The catalog is the simplest place to make suite identity explicit and auditable.

**Recommended behavior:**
- Resolve only curated suite IDs such as `suite_fixtures_v1`, `suite_smoke`, and a new `suite_hybrid_smoke_v1`.
- Persist the resolved manifest path on `EvaluationRun`, but never take that path directly from the API caller.
- Keep raw `--suite path` only as a developer compatibility path, not the supported control-plane surface.

### Pattern 2: EvaluationRun as Aggregate, Case Results as Children

**What:** Preserve `EvaluationRun` as the aggregate row, but add a first-class `EvaluationCaseResult` child table for stored case outcomes.

**When to use:** Any persisted evaluation run created through the control plane.

**Why:** The aggregate row already fits project ownership and lifecycle state, but Phase 09 needs case-level reopening and filtering without reparsing `results_json`.

**Recommended child fields:**
- `evaluation_run_id`
- `case_id`
- `input_mode`
- `status`
- `degradation_class`
- `run_goal`
- `message`
- `policy_json`
- `observation_json`
- `checks_json`
- `metadata_json`
- `artifacts_json`

### Pattern 3: API-Backed Create Then Start

**What:** Separate persistence of a pending evaluation row from explicit execution of that row through a start endpoint or equivalent service call.

**When to use:** Supported evaluation workflows in this phase.

**Why:** It keeps the control plane inspectable and auditable even when execution later fails, and it matches the existing product tendency to separate resource creation from execution transitions.

**Recommended routes:**
- `GET /v1/evaluations/suites`
- `GET /v1/evaluations?project_id=...`
- `POST /v1/evaluations`
- `GET /v1/evaluations/{evaluation_run_id}`
- `POST /v1/evaluations/{evaluation_run_id}/start`
- `GET /v1/evaluations/{evaluation_run_id}/cases`

### Pattern 4: Shared Execution Service, Not Duplicated Glue

**What:** Put suite resolution, lifecycle updates, runner invocation, summary persistence, and case-result writes behind one backend service.

**When to use:** API start flows and any CLI compatibility mode that should persist supported evaluation runs.

**Why:** The current drift problem comes from one-off CLI orchestration. A shared service keeps API and CLI semantics aligned without forcing the CLI to talk HTTP to itself.

**Recommended behavior:**
- Resolve the suite from the catalog
- mark the row `running`
- run `EvaluationRunner(... allow_live_cases=...)`
- persist `summary_json` and a backward-compatible `results_json` export
- replace case-result rows for the evaluation run with persisted child records
- mark terminal `passed` / `failed` / `skipped` / `error`

### Pattern 5: Review Surfaces Stay Summary-First and Project-Scoped

**What:** Reopen evaluation history through a summary aggregate plus separate case-result resources, all behind the existing owner-project boundary.

**When to use:** Evaluation list/detail/case review routes.

**Why:** Phase 08 already established a summary-first product posture, and Phase 09 decisions explicitly rejected a new operator-global auth model.

**Recommended review behavior:**
- evaluation run detail returns summary metadata plus counts
- case list supports `status`, `input_mode`, and `degradation_class` filters
- one case-detail route returns full stored case context without forcing clients to parse `results_json`

## Implementation Slices

### Slice A: Catalog, Persistence, and API Foundation

Focus files:
- `edgar_project/evaluation/catalog.py`
- `edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json`
- `alembic/versions/012_evaluation_control_plane_case_results.py`
- `backend/models/evaluation_case_result.py`
- `backend/models/evaluation_run.py`
- `backend/schemas/evaluation_run.py`
- `backend/schemas/evaluation_case_result.py`
- `backend/api/routes/evaluations.py`
- `tests/test_evaluation_control_plane_api.py`

Deliver:
- curated suite registry
- approved hybrid smoke manifest
- first-class case-result table
- project-scoped evaluation list/create/detail API foundation

### Slice B: Shared Execution Service and Persisted Start Flow

Focus files:
- `backend/repositories/evaluation_run_repository.py`
- `backend/repositories/evaluation_case_result_repository.py`
- `backend/services/evaluation_control_plane_service.py`
- `backend/api/routes/evaluations.py`
- `backend/api/deps.py`
- `tests/test_evaluation_control_plane_service.py`
- `tests/test_evaluation_control_plane_api.py`

Deliver:
- shared service that runs supported suites and persists results
- start endpoint with explicit live opt-in
- stored summary JSON plus first-class case rows populated from runner results

### Slice C: Review Surfaces, CLI Compatibility, and Docs

Focus files:
- `backend/api/routes/evaluations.py`
- `backend/schemas/evaluation_run.py`
- `backend/schemas/evaluation_case_result.py`
- `edgar_project/cli.py`
- `edgar_project/evaluation/README.md`
- `README.md`
- `tests/test_evaluation_control_plane_api.py`
- `tests/test_evaluation_cli_compat.py`

Deliver:
- explicit case list/detail review routes
- CLI compatibility path that resolves supported suite IDs
- docs that distinguish the API-backed supported workflow from raw path-based dev tooling

## Validation Architecture

Phase 09 needs Wave 0 tests because there is no existing evaluation API or service test coverage.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_evaluation_control_plane_api.py tests/test_evaluation_control_plane_service.py tests/test_evaluation_cli_compat.py -q --tb=short
```

**Recommended full command:**
```bash
python3 -m pytest tests/ -q --tb=short
```

**Required new tests:**
- `tests/test_evaluation_control_plane_api.py`
  - suite catalog endpoint returns curated IDs only
  - create/list/detail are project-scoped
  - create persists resolved manifest path instead of caller-supplied path
  - case review routes reopen stored per-case results
- `tests/test_evaluation_control_plane_service.py`
  - shared service persists lifecycle state transitions
  - case rows store `input_mode`, `status`, `degradation_class`, `policy_json`, and `observation_json`
  - aggregate `summary_json` / `results_json` stay backward-compatible exports derived from stored case rows
- `tests/test_evaluation_cli_compat.py`
  - CLI accepts `--suite-id` for supported suites
  - unknown supported suite IDs fail cleanly
  - persisted compatibility mode delegates into the same control-plane service rather than bypassing it

## Pitfalls and Boundaries

- Do not expose arbitrary repo file paths as the supported API contract.
- Do not keep case outcomes only inside `results_json`.
- Do not introduce child `AnalysisRun` linkage or worker orchestration in this phase.
- Do not invent a global operator auth model outside the existing project-owner boundary.
- Do not let CLI compatibility become the canonical workflow again; API-backed persisted runs remain the source of truth.

## Recommended Plan Shape

Phase 09 should be planned as **3 sequential plans**:

1. **Catalog and API foundation** — curated suite registry, case-result persistence, and project-scoped evaluation list/create/detail routes
2. **Execution service** — shared service and start route that persist runner outputs into first-class records
3. **Review and compatibility** — case-review endpoints, CLI compatibility, docs, and regression hardening

This sequence keeps the contract and storage layer first, the execution semantics second, and the compatibility/review finish last.

## Sources

### Primary
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/09-evaluation-control-plane/09-CONTEXT.md`
- `.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md`
- `.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md`
- `backend/models/evaluation_run.py`
- `backend/schemas/evaluation_run.py`
- `backend/auth/resource_access.py`
- `backend/api/router.py`
- `edgar_project/evaluation/schemas.py`
- `edgar_project/evaluation/runner.py`
- `edgar_project/evaluation/summary_report.py`
- `edgar_project/evaluation/benchmarks/suite_fixtures_v1.json`
- `edgar_project/evaluation/benchmarks/suite_smoke.json`
- `edgar_project/cli.py`

### Secondary
- `backend/services/artifact_service.py`
- `backend/models/project.py`
- `tests/test_evaluation_policy_contract.py`
- `tests/test_evaluation_runner_policy.py`
- `tests/test_run_lifecycle_api.py`
