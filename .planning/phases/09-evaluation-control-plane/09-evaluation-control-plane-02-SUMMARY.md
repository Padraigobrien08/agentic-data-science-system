---
phase: 09-evaluation-control-plane
plan: 02
subsystem: backend
tags: [evaluation, api, persistence, execution]
requires: ["09-01"]
provides:
  - "Shared execution service for persisted supported evaluation runs"
  - "API-backed `/start` flow for fixture, live, and hybrid supported suites"
  - "Backward-compatible aggregate `results_json` plus first-class persisted case rows"
affects: [backend, api, evaluation]
tech-stack:
  added: []
  patterns: ["shared execution service", "configured temp output workspace", "aggregate-plus-child persistence"]
key-files:
  created:
    - backend/repositories/evaluation_run_repository.py
    - backend/repositories/evaluation_case_result_repository.py
    - backend/services/evaluation_control_plane_service.py
    - tests/test_evaluation_control_plane_service.py
  modified:
    - backend/services/__init__.py
    - backend/api/deps.py
    - backend/api/routes/evaluations.py
    - tests/test_evaluation_control_plane_api.py
key-decisions:
  - "Supported evaluation starts execute through one shared service instead of duplicating runner logic inside the route layer."
  - "Suite output is redirected into a temp workspace outside the repo so API-backed starts do not dirty tracked evaluation directories."
  - "The control plane keeps `summary_json` and `results_json` aligned with the existing runner export while persisting first-class case rows."
patterns-established:
  - "Persisted evaluation workflows should treat `EvaluationRun` as the aggregate state and `EvaluationCaseResult` as the case review surface."
  - "Live and hybrid opt-in stays explicit at the API boundary through `allow_live`, even when the runner still returns skipped outcomes."
requirements-completed: []
duration: 18min
completed: 2026-04-18
---

# Phase 09: Evaluation Control Plane Summary

**Shared execution service and persisted API-backed starts**

## Performance

- **Duration:** 18 min
- **Completed:** 2026-04-18T16:16:54Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added repositories plus a shared `EvaluationControlPlaneService` that transitions stored evaluation runs through `pending`, `running`, and terminal persisted states.
- Persisted per-case `policy_json`, `observation_json`, `degradation_class`, and runner metadata while keeping `summary_json` and `results_json` as backward-compatible aggregate exports.
- Added `/v1/evaluations/{evaluation_run_id}/start` with explicit `allow_live` handling, owner-scoped access, and `409` rejection for non-pending runs.

## Task Commits

1. **Task 1-2: Shared execution service and API-backed start flow** - `e369d0b` (`feat(09-02): persist supported evaluation execution`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/repositories/evaluation_run_repository.py` - lockable evaluation-run persistence helpers plus case-count queries
- `backend/repositories/evaluation_case_result_repository.py` - case-result replacement and query helpers
- `backend/services/evaluation_control_plane_service.py` - shared start-flow execution and persistence logic
- `backend/api/routes/evaluations.py` - synchronous start endpoint layered onto the existing project-scoped evaluation API
- `tests/test_evaluation_control_plane_service.py` - service-level coverage for fixture, live, and hybrid persisted starts
- `tests/test_evaluation_control_plane_api.py` - API coverage for `/start`, `allow_live`, persisted case rows, and non-pending conflicts

## Decisions Made

- Persisted evaluation starts now execute supported suites in a temp output root outside the repo, preserving runner artifact paths without polluting tracked directories.
- The route layer stays thin: ownership and pending checks happen in the API boundary, while execution and persistence stay in the service.

## Deviations from Plan

- **[Rule 3 - Blocking] Existing `STATE.md` milestone regression still quarantined** — Found during: ongoing phase execution | Issue: the earlier `state begin-phase` helper mutation still leaves `.planning/STATE.md` dirty with bad `v1.0` milestone metadata | Fix: kept that file out of the Wave 2 commit and will repair it during phase closeout | Files modified: none committed in this wave | Verification: `git status --short` still shows `.planning/STATE.md` as a separate uncommitted change | Commit hash: n/a

**Total deviations:** 1 inherited planning-state issue. **Impact:** no product-code impact; manual state repair still required before final phase completion.

## Issues Encountered

- Service tests initially seeded evaluation-run IDs as strings, which broke the new repository `with_for_update` UUID path. Fixing the test helper to return real UUIDs resolved the failure immediately.

## User Setup Required

None.

## Next Phase Readiness

- Wave 3 can build directly on the persisted case-result seam and the new `/start` route.
- CLI compatibility and case review routes no longer need to invent execution behavior; they can reuse the shared control-plane service and stored child rows.

## Self-Check

- `python3 -m pytest tests/test_evaluation_control_plane_service.py tests/test_evaluation_control_plane_api.py -q --tb=short`

---
*Phase: 09-evaluation-control-plane*
*Completed: 2026-04-18*
