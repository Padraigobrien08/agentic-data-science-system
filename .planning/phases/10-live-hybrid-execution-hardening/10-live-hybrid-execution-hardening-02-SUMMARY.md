---
phase: 10-live-hybrid-execution-hardening
plan: 02
subsystem: backend
tags: [evaluation, runs, api, reconciliation]
requires: ["10-01"]
provides:
  - "Queue-backed live and hybrid evaluation starts that return immediately in a truthful running state"
  - "Case and aggregate evaluation verdicts reconciled from linked child `AnalysisRun` truth"
  - "API coverage for case-to-run navigation and degradation-aware refresh on evaluation reads"
affects: [backend, api, evaluation, tests]
tech-stack:
  added: []
  patterns: ["canonical child-run reconciliation", "read-time evaluation refresh", "case-to-run navigation"]
key-files:
  created:
    - .planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md
  modified:
    - backend/services/evaluation_control_plane_service.py
    - backend/api/routes/evaluations.py
    - edgar_project/evaluation/runner.py
    - tests/test_evaluation_live_hybrid_execution.py
    - tests/test_evaluation_control_plane_api.py
    - tests/test_evaluation_control_plane_service.py
key-decisions:
  - "Live and hybrid supported evaluations now use the control plane as a thin scheduler over canonical child runs instead of inline placeholder execution."
  - "Evaluation case status remains `pending` while the linked child run is non-terminal; aggregate evaluation status remains `running` until all linked cases settle."
  - "SEC and storage failure evidence is persisted on case metadata for later ops surfaces instead of being buried only in run error text."
patterns-established:
  - "Evaluation reads refresh child-run-backed case truth before serializing operator-facing responses."
  - "The shared validation degradation taxonomy is reused from the runner through a pure helper rather than duplicated in the control plane."
requirements-completed: []
duration: 18min
completed: 2026-04-18
---

# Phase 10: Live/Hybrid Execution Hardening Summary

**Queue-backed launch and canonical verdict reconciliation**

## Performance

- **Duration:** 18 min
- **Completed:** 2026-04-18T19:45:00Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Converted supported live and hybrid evaluation starts into queued child-run launches that return `running` immediately.
- Added read-time reconciliation so evaluation detail and case routes derive case and aggregate verdicts from linked `AnalysisRun` truth.
- Added regression coverage for success, SEC degradation, storage degradation, and direct case-to-run navigation through existing run APIs.

## Task Commits

1. **Task 1-2: Async child-run launch and canonical verdict refresh** - pending commit

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/services/evaluation_control_plane_service.py` - async live/hybrid launch path, canonical child-run reconciliation, and aggregate snapshot rebuilding
- `backend/api/routes/evaluations.py` - evaluation detail and case routes now refresh linked child-run state before serializing responses
- `edgar_project/evaluation/runner.py` - extracted reusable degradation classifier for control-plane reconciliation
- `tests/test_evaluation_live_hybrid_execution.py` - queue-backed start and terminal child-run truth coverage
- `tests/test_evaluation_control_plane_api.py` - route refresh and run-navigation regressions
- `tests/test_evaluation_control_plane_service.py` - updated older service assertions to the queue-backed contract

## Decisions Made

- The control plane still preserves the Phase 09 synchronous path for fixture-only suites.
- Storage failures remain classified as `product_regression` today, but now carry explicit `storage_error_code` evidence for Phase 10 observability.

## Deviations from Plan

- `backend/schemas/evaluation_run.py` and `backend/schemas/evaluation_case_result.py` did not require Wave 2 edits because the Wave 1 linkage fields and generic result payloads already covered the API surface.
- `tests/test_evaluation_control_plane_service.py` was updated in addition to the planned files so the repo no longer carried stale pre-Phase-10 expectations.

## Issues Encountered

- The first pass left cached child-run history entries stuck at `queued`; the fix was to rewrite the JSON history item on reconciliation instead of mutating the nested dict in place.

## User Setup Required

None.

## Next Phase Readiness

- Wave 3 can now read explicit SEC and storage failure evidence from evaluation case metadata without scraping opaque summary blobs.
- Health and metrics work can treat evaluation dependency truth as a DB-backed read over canonical child-run-linked case rows.

## Self-Check

- `python3 -m pytest tests/test_evaluation_live_hybrid_execution.py tests/test_evaluation_control_plane_api.py -q --tb=short`
- `python3 -m pytest tests/test_evaluation_control_plane_service.py tests/test_evaluation_runner_policy.py -q --tb=short`

---
*Phase: 10-live-hybrid-execution-hardening*
*Completed: 2026-04-18*
