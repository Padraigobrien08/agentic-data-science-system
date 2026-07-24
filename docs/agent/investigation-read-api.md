# Investigation Read-API & UI

Read-only surfaces for the generalized investigation model — the structured state
(`agentic/domain`) persisted by the adaptive loop. They make agency **inspectable**:
what hypotheses were tested, what evidence was gathered, what the agent decided and why,
and how the run terminated.

## Creating an investigation (the entry point)

`POST /v1/investigations` turns the flag-gated engine into something a user can start:

- Body: `{project_id, goal, dataset}` where `dataset` is either pasted CSV
  (`{format: "csv", csv_text, name?, time_field?, entity_id_fields?}`) or inline records
  (`{format: "records", records: [...]}`).
- It creates an `AnalysisRun` opting into the agentic engine (`input_payload_json.engine =
  "agentic"`, `in_memory` adapter) and returns
  `{analysis_run_id, investigation_id, status, db_status, queued}`.
- **Execution mode.** Default is **synchronous** (best for small pasted datasets; works with no
  worker). `async_execution: true` **enqueues** the run for the worker instead — robust for
  larger datasets, but requires a running worker with the flag enabled. When queued,
  `investigation_id` is `null` until the worker persists it; resolve it with
  `GET /v1/investigations?analysis_run_id=…` (owner-scoped). The UI's pending page
  (`investigations/pending/[runId]`) polls this and redirects to the detail when it lands.
- `409` when the engine flag is off; `400` on an empty/malformed/oversized dataset;
  owner-scoped to the project (`404` otherwise). CSV parsing (typed coercion, row/column
  caps) and flag-gating live in `backend/services/investigation_create_service.py`.
- Fully **input-agnostic**: arbitrary column names, no EDGAR/domain assumptions — the general
  profilers infer roles/semantic types. With no LLM configured the run uses the deterministic
  fixture policy; with one configured it uses the model-backed policy.

`GET /v1/health` exposes `agentic_engine_enabled` so surfaces can gate the entry point.

## Backend API (owner-scoped)

Registered under the `/v1` prefix (`backend/api/routes/investigations.py`); every request
requires an authenticated user and is scoped to investigations the user can access (owner of
the linked project, or the initiating user). Missing/unauthorized → `404`.

- `GET /v1/investigations` — list summaries, newest first.
  - `project_id` (optional) scopes to one owned project.
  - `limit` (1–500, default 100), `offset` (default 0).
  - Each `InvestigationSummary` carries status, confidence, objective, the current
    conclusion statement, per-entity `counts`, and `analysis_run_id` (so a client can map a
    run to its investigation).
- `GET /v1/investigations/{id}` — full `InvestigationDetail`: hypotheses (with prior→posterior
  confidence and linked evidence), evidence (direction/strength/reliability/coverage), agent
  decisions (ordered), experiments (tool, status, summary, metrics), critiques, open
  questions, the conclusion, termination, datasets, and the append-only event timeline.

Projection lives in `backend/schemas/investigation.py` (`build_summary` / `build_detail`),
mapping the normalized rows (`backend/models/investigation*.py`) to stable wire shapes.
Ownership: `backend/auth/resource_access.py:get_investigation_for_owner` +
`backend/api/access_checks.py:require_investigation_owned`.

## Frontend

Server components under `frontend/src/app/projects/[projectId]/investigations/`:

- **List** (`page.tsx`) → `InvestigationSummaryList` — status pill, conclusion preview, and
  hypotheses/evidence/experiments/decisions counts per investigation. Shows a **New
  investigation** button when the engine is enabled.
- **New** (`new/page.tsx`) → `NewInvestigationForm` — goal + pasted CSV (+ optional
  time/entity columns) → `createInvestigationAction` → runs and redirects to the detail.
- **Detail** (`[investigationId]/page.tsx`) → `InvestigationDetailView` — header (objective,
  status, confidence, termination), conclusion card, hypotheses with their linked evidence and
  a confidence-delta indicator, the agent-decision timeline, experiments, open critiques, and
  open questions.

Data access: `frontend/src/lib/api/investigations.ts` (`listInvestigations`, `getInvestigation`).
Pure view helpers (status/disposition tones, confidence formatting, evidence linking) live in
`frontend/src/lib/investigation-view.ts` and are unit-tested. Discovery: a path-aware
`InvestigationsNavLink` in the site header surfaces the list from any project route.

## Agency evaluation

`tests/test_agentic_agency_evaluation.py` drives the create path over a **non-EDGAR** CSV and
asserts the agency properties on the persisted investigation: input-agnosticism, adaptivity
(different goals take different experiment paths), hypothesis movement under contradictory
evidence, and typed termination (insufficient data → `insufficient_evidence`). This
complements the loop-level behavior tests in `tests/agentic/test_investigation_loop.py`.

Tests: `tests/test_investigation_read_api.py`, `tests/test_investigation_create.py`,
`tests/test_agentic_agency_evaluation.py` (backend);
`frontend/src/lib/__tests__/investigation-view.test.ts` (frontend).
