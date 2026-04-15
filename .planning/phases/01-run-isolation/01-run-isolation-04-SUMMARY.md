---
phase: 01-run-isolation
plan: 04
subsystem: tests
tags: [run-isolation, pytest, mcp, orchestration, regression, overlap]
requires:
  - phase: 01-03
    provides: Backend provenance persistence, no-cwd entrypoints, and shared run-workspace deployment wiring
provides:
  - Real overlapping-run regression coverage that writes Phase 1 artifacts into separate workspaces
  - MCP/orchestration/report regression suites that enforce run-scoped processed/artifact roots
  - Explicit legacy opt-in coverage for shared artifact-path fallbacks
affects: [phase-completion, tests, mcp, orchestration, report]
tech-stack:
  added: []
  patterns: [dual-workspace overlap regression, run-scoped MCP fixtures, explicit legacy footer opt-in]
key-files:
  created: []
  modified: [tests/test_run_isolation_workspace.py, tests/test_run_isolation_overlap.py, tests/mcp/conftest.py, tests/mcp/test_tools.py, tests/test_mcp_orchestration_artifact_contract.py, tests/orchestration/test_phase3_orchestration.py, tests/test_report_credibility.py]
key-decisions:
  - "Replace the Wave 0 overlap seed with a real end-to-end write-path regression instead of a skipped placeholder."
  - "Model MCP fixture artifacts under `run-123/processed` and `run-123/artifacts` so test fixtures match the production workspace layout."
  - "Keep shared `data/artifacts` footer behavior only behind explicit legacy opt-in in report tests."
patterns-established:
  - "Overlap safety pattern: two concrete workspaces write the same Phase 1 roles and must produce distinct paths for every shared artifact key."
  - "Regression hardening pattern: planner labels, MCP payload models, and report footer behavior all assert explicit-path execution in the normal branch."
requirements-completed: [EXEC-01, EXEC-02]
duration: 1min
completed: 2026-04-15
---

# Phase 1 Plan 04: Regression Hardening Summary

**Phase 1 is now locked by direct overlap, MCP/orchestration, and report-path regressions**

## Performance

- **Duration:** 1 min
- **Started:** 2026-04-15T12:20:38Z
- **Completed:** 2026-04-15T12:21:19Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Replaced the Wave 0 overlap placeholder with a real regression that writes Phase 1 artifacts into `run-a` and `run-b` workspaces and proves their shared artifact roles do not collide.
- Moved MCP fixture paths to a run-scoped processed/artifacts layout and added input-model assertions so `run_workspace` remains part of the normal explicit-path contract.
- Tightened orchestration and report tests so `generate_report:explicit_paths` and legacy footer/default-path behavior stay explicit rather than implicit.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add focused regression tests for workspace construction and overlap isolation**
   `7f80ec5` (`test`) overlap isolation regression and workspace-path contract tightening
2. **Task 2: Update existing MCP, orchestration, and report regressions to assert explicit-path execution**
   `f630df7` (`test`) run-scoped fixture layout and explicit-path regression hardening

## Files Created/Modified

- `tests/test_run_isolation_workspace.py` - Renames the core path contract check to the persisted run-scoped workspace expectation and tightens directory assertions.
- `tests/test_run_isolation_overlap.py` - Replaces the skip-only seed with a real dual-workspace write regression.
- `tests/mcp/conftest.py` - Builds fixture artifacts under `run-123/processed` and `run-123/artifacts`.
- `tests/mcp/test_tools.py` - Asserts MCP input models accept `run_workspace` and that workspace payloads are threaded in normal explicit-path tool flows.
- `tests/test_mcp_orchestration_artifact_contract.py` - Uses run-scoped processed/artifact paths plus explicit shared `manual_validation_csv` in merge-contract assertions.
- `tests/orchestration/test_phase3_orchestration.py` - Asserts the report step label is `generate_report:explicit_paths` and that planned report params keep legacy fallback disabled.
- `tests/test_report_credibility.py` - Makes legacy footer path rendering explicit opt-in instead of relying on the zero-argument branch.

## Decisions Made

- Kept `manual_validation_csv` represented as an explicit shared input path in regression fixtures instead of moving it into workspace artifacts.
- Used real file writes in the overlap test rather than path-only assertions so collisions would surface as behavior regressions, not just contract drift.
- Left the normal branch centered on run-scoped paths while preserving one explicit legacy coverage path for shared artifact lookup behavior.

## Deviations from Plan

None.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- Phase 1 success criteria are now backed by runtime changes plus direct regressions for overlap, provenance, and no-cwd execution.
- The next meaningful project step is Phase `02` (`Worker Resilience`); no remaining Phase 1 blockers were found.
- Recommended next action: discuss or plan Phase 2.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/01-run-isolation/01-run-isolation-04-SUMMARY.md`.
- Task commits verified in git history: `7f80ec5`, `f630df7`.
- Full Phase 1 regression sweep passed: `python3 -m pytest tests/test_backend_foundation.py tests/test_run_isolation_execution_service.py tests/test_run_isolation_entrypoints.py tests/test_run_isolation_workspace.py tests/test_run_isolation_overlap.py tests/mcp/test_tools.py tests/test_mcp_orchestration_artifact_contract.py tests/orchestration/test_phase3_orchestration.py tests/test_report_credibility.py tests/test_metric_coverage.py tests/test_metric_caveats.py tests/test_deterioration_focus.py tests/test_trustworthiness_contracts.py -q`.

---
*Phase: 01-run-isolation*
*Completed: 2026-04-15*
