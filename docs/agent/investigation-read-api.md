# Investigation Read-API & UI

Read-only surfaces for the generalized investigation model — the structured state
(`agentic/domain`) persisted by the adaptive loop. They make agency **inspectable**:
what hypotheses were tested, what evidence was gathered, what the agent decided and why,
and how the run terminated.

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
  hypotheses/evidence/experiments/decisions counts per investigation.
- **Detail** (`[investigationId]/page.tsx`) → `InvestigationDetailView` — header (objective,
  status, confidence, termination), conclusion card, hypotheses with their linked evidence and
  a confidence-delta indicator, the agent-decision timeline, experiments, open critiques, and
  open questions.

Data access: `frontend/src/lib/api/investigations.ts` (`listInvestigations`, `getInvestigation`).
Pure view helpers (status/disposition tones, confidence formatting, evidence linking) live in
`frontend/src/lib/investigation-view.ts` and are unit-tested. Discovery: a path-aware
`InvestigationsNavLink` in the site header surfaces the list from any project route.

Tests: `tests/test_investigation_read_api.py` (backend) and
`frontend/src/lib/__tests__/investigation-view.test.ts` (frontend).
