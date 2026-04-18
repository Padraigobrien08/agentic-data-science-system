---
phase: 09-evaluation-control-plane
plan: 01
subsystem: backend
tags: [evaluation, api, persistence, catalog]
requires: []
provides:
  - "Curated supported-suite catalog for fixture, live, and hybrid evaluation workflows"
  - "First-class `evaluation_case_results` persistence under `EvaluationRun`"
  - "Project-scoped evaluation suite, create, list, and detail API foundation"
affects: [backend, api, evaluation]
tech-stack:
  added: []
  patterns: ["curated suite registry", "aggregate-plus-child persistence", "project-scoped evaluation API"]
key-files:
  created:
    - edgar_project/evaluation/catalog.py
    - edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json
    - alembic/versions/012_evaluation_control_plane_case_results.py
    - backend/models/evaluation_case_result.py
    - backend/schemas/evaluation_case_result.py
    - backend/api/routes/evaluations.py
    - tests/test_evaluation_control_plane_api.py
  modified:
    - backend/models/evaluation_run.py
    - backend/models/__init__.py
    - backend/schemas/evaluation_run.py
    - backend/schemas/__init__.py
    - backend/api/access_checks.py
    - backend/api/router.py
key-decisions:
  - "Supported product-facing evaluation launches now resolve only curated suite IDs rather than caller-supplied manifest paths."
  - "Case-level outcomes are stored in a dedicated child table instead of relying only on `results_json`."
  - "Evaluation API ownership follows the existing project-owner boundary with consistent `404` behavior for non-owned resources."
patterns-established:
  - "Evaluation workflows should mirror the existing product model: persisted aggregate row first, execution logic later."
  - "Supported suite identity is a catalog concern, not a free-form path passed through API requests."
requirements-completed: []
duration: 14min
completed: 2026-04-18
---

# Phase 09: Evaluation Control Plane Summary

**Catalog, persistence foundation, and project-scoped API surface**

## Performance

- **Duration:** 14 min
- **Completed:** 2026-04-18T16:06:47Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added a supported-suite catalog with explicit fixture, live smoke, and hybrid smoke suite IDs.
- Introduced `evaluation_case_results` as a first-class persisted child resource under `EvaluationRun`.
- Added the initial `/v1/evaluations` API surface for suite listing and pending evaluation-run create/list/detail flows.

## Task Commits

1. **Task 1-2: Catalog, case-result persistence, and API foundation** - `19f7795` (`feat(09-01): add evaluation control plane foundation`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `edgar_project/evaluation/catalog.py` - curated supported-suite registry used by the control plane
- `edgar_project/evaluation/benchmarks/suite_hybrid_smoke_v1.json` - supported hybrid smoke scaffold with explicit live-policy metadata
- `alembic/versions/012_evaluation_control_plane_case_results.py` - migration for first-class case-result persistence
- `backend/models/evaluation_case_result.py` - ORM model for stored per-case outcomes
- `backend/schemas/evaluation_run.py` - narrowed public create schema and added `case_count`
- `backend/schemas/evaluation_case_result.py` - typed case-result read schema
- `backend/api/routes/evaluations.py` - project-scoped suite/create/list/detail routes
- `tests/test_evaluation_control_plane_api.py` - API coverage for curated suite IDs and owner-scoped evaluation rows

## Decisions Made

- Stored `suite_manifest_path` is catalog-derived and repo-relative; callers cannot define it through the create API.
- The first supported evaluation routes require `project_id` explicitly to keep the control plane project-scoped by default.

## Deviations from Plan

- **[Rule 3 - Blocking] `state begin-phase` milestone regression** — Found during: execution setup | Issue: the GSD `state begin-phase` command rewrote `.planning/STATE.md` milestone fields to `v1.0` / `milestone` instead of preserving the current `v1.1` metadata | Fix: left the bad state change uncommitted and will repair state manually during phase closeout | Files modified: none committed yet | Verification: `git diff -- .planning/STATE.md` showed the regression before any state commit | Commit hash: n/a

**Total deviations:** 1 auto-contained setup issue. **Impact:** no product-code impact; planning state requires manual repair before phase completion.

## Issues Encountered

- The phase-start helper updates execution status correctly but clobbers milestone metadata in `STATE.md`, so the phase closeout will repair that file manually instead of trusting the helper output.

## User Setup Required

None.

## Next Phase Readiness

- Wave 2 can build directly on the new `EvaluationRun` + `EvaluationCaseResult` persistence seam.
- The execution service can now target a stable suite catalog and a project-scoped API contract instead of inventing those at runtime.

## Self-Check

- `python3 -m pytest tests/test_evaluation_control_plane_api.py -q --tb=short`

---
*Phase: 09-evaluation-control-plane*
*Completed: 2026-04-18*
