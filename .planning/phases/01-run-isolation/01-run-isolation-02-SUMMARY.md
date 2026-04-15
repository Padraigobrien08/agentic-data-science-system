---
phase: 01-run-isolation
plan: 02
subsystem: infra
tags: [run-isolation, mcp, orchestration, report, pytest]
requires:
  - phase: 01-01
    provides: RunWorkspace contract, payload schema, and workspace-aware Phase 1 path registry
provides:
  - Explicit workspace-threaded Phase 1 writers and report readers
  - MCP tool inputs that accept and propagate run_workspace payloads
  - Orchestration planner/executor wiring for generate_report explicit paths
affects: [01-03, 01-04, backend, mcp, src, report]
tech-stack:
  added: []
  patterns: [workspace-aware artifact resolution, explicit-path report generation, orchestration path injection]
key-files:
  created: []
  modified: [src/pipeline_runner.py, src/report.py, src/manual_validation.py, edgar_project/mcp/tools.py, edgar_project/orchestration/executor.py, edgar_project/orchestration/planner.py]
key-decisions:
  - "Normal execution stays on run-scoped workspace paths; shared Phase 1 paths remain legacy-only opt-in."
  - "The MCP boundary accepts run_workspace payloads and forwards them to report/pipeline helpers instead of reconstructing shared defaults."
  - "The orchestration executor injects upstream artifact paths into compute/anomaly/report steps when the planner leaves those fields empty."
patterns-established:
  - "Runtime path threading: plan steps may omit concrete feature/anomaly/report paths, but executor fills them from accumulated artifact_paths plus run_workspace."
  - "Workspace-aware reporting: report generation receives workspace metadata and explicit artifact maps so provenance sections stay run-scoped."
requirements-completed: [EXEC-01, EXEC-02]
duration: 20min
completed: 2026-04-15
---

# Phase 1 Plan 02: Explicit Path Runtime Summary

**Workspace-scoped Phase 1 writers, report readers, MCP tools, and orchestration now resolve artifacts from explicit run paths instead of repo-global defaults**

## Performance

- **Duration:** 20 min
- **Started:** 2026-04-15T11:43:25Z
- **Completed:** 2026-04-15T12:03:40Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments

- Refactored Phase 1 writers and report/manual-validation readers to work from `RunWorkspace` and explicit artifact-path maps.
- Added MCP-side `run_workspace` threading for `generate_report` and `run_pipeline`, including explicit-path planner/executor support.
- Expanded regression coverage so report credibility, trustworthiness contracts, and orchestration now fail if the system drifts back to shared default paths.

## Task Commits

Each task was committed atomically:

1. **Task 1: Refactor Phase 1 writers and report/manual-validation readers to consume explicit workspace paths**
   `a9ff76e` (`test`) RED workspace/report path regressions
   `a47cc9e` (`feat`) workspace-aware writers and report/manual-validation path refactor
2. **Task 2: Thread workspace data through MCP and orchestration without default-path fallbacks**
   `e4a1270` (`test`) RED MCP/orchestration workspace-threading regressions
   `5dab4ad` (`feat`) MCP/orchestration workspace threading and explicit report dispatch

## Files Created/Modified

- `src/pipeline_runner.py` - Writes all normal Phase 1 outputs through `RunWorkspace`.
- `src/report.py` - Resolves credibility/trustworthiness artifacts from explicit workspace-aware path maps.
- `src/manual_validation.py` - Keeps manual validation as an explicit shared input instead of a repo-global output assumption.
- `src/data_quality.py`, `src/exclusions.py`, `src/metric_caveats.py` - Remove normal-mode hardcoded shared-path provenance strings.
- `edgar_project/mcp/schemas.py` and `edgar_project/mcp/server.py` - Accept `run_workspace` on MCP inputs and tool wrappers.
- `edgar_project/mcp/adapters.py` and `edgar_project/mcp/tools.py` - Resolve workspace payloads and pass them through report/pipeline helpers.
- `edgar_project/orchestration/planner.py` and `edgar_project/orchestration/executor.py` - Use `generate_report:explicit_paths` and inject upstream artifact paths plus `run_workspace`.
- `tests/mcp/test_tools.py`, `tests/test_mcp_orchestration_artifact_contract.py`, `tests/orchestration/test_phase3_orchestration.py` - Lock in MCP/orchestration explicit-path behavior.
- `tests/test_report_credibility.py`, `tests/test_metric_coverage.py`, `tests/test_metric_caveats.py`, `tests/test_deterioration_focus.py`, `tests/test_trustworthiness_contracts.py` - Lock in workspace-scoped report/trustworthiness behavior.

## Decisions Made

- Reused the shared `RunWorkspace` payload at the MCP boundary instead of inventing a second path contract.
- Let the executor inject concrete upstream artifact paths into later MCP steps when planner placeholders are `None`.
- Preserved the legacy `use_default_artifact_paths` branch only as an explicit opt-in, while making the normal granular report flow use `explicit_paths`.

## Deviations from Plan

### Auto-fixed Issues

**1. [Execution continuity] Completed Task 2 locally after the executor stalled without writing plan metadata**
- **Found during:** Task 2 (Thread workspace data through MCP and orchestration without default-path fallbacks)
- **Issue:** The executor produced the RED commit and most of the MCP/orchestration edits, but never wrote `01-run-isolation-02-SUMMARY.md` or the final feature commit.
- **Fix:** Finished the remaining workspace-threading changes locally, reran the full Plan 02 verification suite, and recorded the missing summary/progress metadata without changing plan scope.
- **Files modified:** `edgar_project/mcp/adapters.py`, `edgar_project/mcp/tools.py`, `.planning/phases/01-run-isolation/01-run-isolation-02-SUMMARY.md`, `.planning/ROADMAP.md`, `.planning/STATE.md`
- **Verification:** `python3 -m pytest tests/test_run_isolation_workspace.py tests/test_report_credibility.py tests/test_metric_coverage.py tests/test_metric_caveats.py tests/test_deterioration_focus.py tests/test_trustworthiness_contracts.py tests/mcp/test_tools.py tests/test_mcp_orchestration_artifact_contract.py tests/orchestration/test_phase3_orchestration.py -q`
- **Committed in:** `5dab4ad`

---

**Total deviations:** 1 auto-fixed (execution continuity)
**Impact on plan:** No scope change. The only deviation was finishing the planned Task 2 work after the executor stalled.

## Issues Encountered

- The Wave 2 executor stopped without emitting a completion signal or writing plan metadata. Spot-checks plus the RED/feature commits showed partial progress, so the remaining Task 2 MCP/orchestration wiring was finished and re-verified locally.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Backend, CLI, and direct entrypoints can now inherit one shared runtime workspace contract in Plan `01-03`.
- The orchestration path now passes run-scoped artifact locations end-to-end, so Phase `01-04` can focus on regression depth rather than missing wiring.
- No blockers identified for the next run-isolation wave.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/01-run-isolation/01-run-isolation-02-SUMMARY.md`.
- Task commits verified in git history: `a9ff76e`, `a47cc9e`, `e4a1270`, `5dab4ad`.
- Full Plan 02 verification suite passed: `69 passed`.

---
*Phase: 01-run-isolation*
*Completed: 2026-04-15*
