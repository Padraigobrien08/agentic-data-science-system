---
phase: 01-run-isolation
plan: 01
subsystem: infra
tags: [run-isolation, workspace, mcp, pytest, pydantic]
requires: []
provides:
  - RunWorkspace contract for durable run-scoped processed and artifact paths
  - Serialized run_workspace orchestration payload for executor handoff
  - Wave 0 overlap and backend provenance regression seed tests
affects: [01-02, 01-03, 01-04, backend, mcp, src]
tech-stack:
  added: []
  patterns: [run workspace contract, explicit legacy opt-in, workspace-aware phase1 path registry]
key-files:
  created: [edgar_project/run_workspace.py, tests/test_run_isolation_overlap.py, tests/test_run_isolation_execution_service.py]
  modified: [config.py, backend/config/settings.py, edgar_project/orchestration/execution_contract.py, edgar_project/orchestration/schemas.py, src/pipeline_runner.py, tests/test_run_isolation_workspace.py, tests/test_trustworthiness_contracts.py, edgar_project/mcp/adapters.py, edgar_project/mcp/tools.py]
key-decisions:
  - "Model run isolation with a frozen RunWorkspace contract that keeps manual_validation_csv as an explicit shared input."
  - "Expose run_workspace as a serialized orchestration context payload before runtime adoption changes land."
  - "Keep remaining shared-path report behavior behind an explicit MCP legacy flag instead of a hidden zero-arg fallback."
patterns-established:
  - "Path resolution pattern: downstream code receives a RunWorkspace and derives Phase 1 paths from it."
  - "Compatibility pattern: shared Phase 1 roots remain available only through explicit legacy branches."
requirements-completed: [EXEC-01, EXEC-02, EXEC-03]
duration: 14min
completed: 2026-04-15
---

# Phase 1 Plan 01: Run Workspace Contract Summary

**Run-scoped workspace metadata, path registry, and Wave 0 isolation tests for deterministic Phase 1 outputs**

## Performance

- **Duration:** 14 min
- **Started:** 2026-04-15T11:04:40Z
- **Completed:** 2026-04-15T11:18:49Z
- **Tasks:** 3
- **Files modified:** 12

## Accomplishments

- Added `edgar_project/run_workspace.py` with a frozen `RunWorkspace` contract, deterministic Phase 1 basenames, and explicit legacy shared-path opt-in.
- Added `run_workspace_root` backend settings and serialized `RunWorkspacePayload` orchestration handoff metadata.
- Seeded Wave 0 overlap and backend execution provenance regression files before runtime adoption work begins.

## Task Commits

Each task was committed atomically:

1. **Task 1: Create the shared RunWorkspace contract and config surface**
   `e25bde2` (`test`) RED contract tests
   `f6de7fa` (`feat`) shared workspace builder and settings surface
2. **Task 2: Expose the workspace payload through orchestration and the Phase 1 path registry**
   `9fd04c8` (`test`) RED payload and run-scoped path tests
   `d711310` (`feat`) orchestration payload model and workspace-aware registry
3. **Task 3: Seed Wave 0 isolation regression modules before runtime adoption**
   `2df679a` (`test`) overlap and execution-service regression seed modules

## Files Created/Modified

- `edgar_project/run_workspace.py` - Canonical run workspace dataclass and Phase 1 output registry.
- `config.py` - Durable `data/runs` root plus legacy labeling for shared processed/artifact paths.
- `backend/config/settings.py` - `run_workspace_root` setting for API and worker processes.
- `edgar_project/orchestration/schemas.py` - `RunWorkspacePayload` model for JSON handoff.
- `edgar_project/orchestration/execution_contract.py` - Reserved `context["run_workspace"]` slot and validated accessor.
- `src/pipeline_runner.py` - Workspace-aware `phase1_paths(workspace)` plus explicit legacy helper.
- `tests/test_run_isolation_workspace.py` - Contract coverage for workspace building, payload serialization, and explicit manual validation input handling.
- `tests/test_run_isolation_overlap.py` - Wave 0 overlap regression seed.
- `tests/test_run_isolation_execution_service.py` - Wave 0 backend provenance regression seed.
- `tests/test_trustworthiness_contracts.py` - Updated trustworthiness contract to use the workspace-aware registry.
- `edgar_project/mcp/adapters.py` - Explicit legacy compatibility branch for current MCP default-path flows.
- `edgar_project/mcp/tools.py` - Explicit `use_legacy_shared_paths=True` call for default-path report generation.

## Decisions Made

- Used a shared `RunWorkspace` contract instead of ad hoc path concatenation so later plans can thread one deterministic payload through `src`, orchestration, MCP, and backend.
- Kept `manual_validation_csv` off the artifact registry and on the workspace contract itself so it remains an explicit shared input rather than a copied per-run file.
- Added an explicit legacy compatibility branch at the MCP boundary so the new workspace-aware registry does not silently drift back to repo-global defaults.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Preserved explicit MCP legacy compatibility after changing the Phase 1 path registry**
- **Found during:** Task 2 (Expose the workspace payload through orchestration and the Phase 1 path registry)
- **Issue:** Making `src.pipeline_runner.phase1_paths` workspace-aware would have left `generate_report_tool` calling the old shared-path seam implicitly.
- **Fix:** Added an explicit `use_legacy_shared_paths=True` compatibility branch in `edgar_project/mcp/adapters.py` and routed `edgar_project/mcp/tools.py` through it.
- **Files modified:** `edgar_project/mcp/adapters.py`, `edgar_project/mcp/tools.py`
- **Verification:** `python3 -m pytest tests/test_mcp_orchestration_artifact_contract.py -q`
- **Committed in:** `d711310`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation kept the new contract strict while avoiding an accidental implicit fallback in the remaining MCP default-path flow.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- The shared workspace builder, payload model, and run-scoped path registry are ready for writer and reader adoption in Plan `01-02`.
- Wave 0 regression seeds now exist, so later plans can expand them instead of introducing overlap and provenance coverage from scratch.
- No blockers identified for the next run-isolation plans.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/01-run-isolation/01-run-isolation-01-SUMMARY.md`.
- Created files verified: `edgar_project/run_workspace.py`, `tests/test_run_isolation_overlap.py`, `tests/test_run_isolation_execution_service.py`.
- Task commits verified in git history: `e25bde2`, `f6de7fa`, `9fd04c8`, `d711310`, `2df679a`.

---
*Phase: 01-run-isolation*
*Completed: 2026-04-15*
