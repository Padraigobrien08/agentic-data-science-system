---
phase: 01-run-isolation
plan: 03
subsystem: backend
tags: [run-isolation, backend, cli, docker-compose, provenance, pytest]
requires:
  - phase: 01-02
    provides: Explicit workspace-threaded Phase 1 writers, report readers, and orchestration path injection
provides:
  - Persisted backend runs anchored to `analysis_run_id` workspaces with stored provenance
  - CLI and `main.py` defaults that use run-scoped workspaces without cwd mutation
  - Shared API/worker run-workspace root wiring in Compose and operator docs
affects: [01-04, backend, cli, docs, deployment]
tech-stack:
  added: []
  patterns: [analysis_run_id workspace provenance, no-cwd entrypoints, shared run workspace volume]
key-files:
  created: [tests/test_run_isolation_entrypoints.py]
  modified: [backend/services/edgar_pipeline_execution_service.py, edgar_project/orchestration/agent.py, tests/test_run_isolation_execution_service.py, main.py, edgar_project/cli.py, edgar_project/console_digest.py, docker-compose.yml, docs/local-stack.md, data/README.md]
key-decisions:
  - "Persisted backend runs derive their workspace from `settings.run_workspace_root` plus `analysis_run_id` and persist the same payload into run and artifact metadata."
  - "Normal CLI and direct entrypoints no longer rely on repo-root `chdir`; they default to generated run-scoped workspaces and print resolved paths."
  - "API and worker deployments must share one configured run-workspace root, with repo-level `data/processed` and `data/artifacts` retained only as explicit legacy/dev paths."
patterns-established:
  - "Backend provenance pattern: the same serialized `run_workspace` payload is stored in `AnalysisRun.meta_json`, passed to orchestration, and attached to ingested artifacts."
  - "Entrypoint migration pattern: live user guidance advertises `data/runs/<run_scoped_id>/...` as the normal branch and avoids implicit cwd setup."
requirements-completed: [EXEC-02, EXEC-03]
duration: 3min
completed: 2026-04-15
---

# Phase 1 Plan 03: Backend and Entrypoint Migration Summary

**Persisted runs, local entrypoints, and deployment docs now use one run-scoped workspace contract without cwd mutation**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-15T12:12:49Z
- **Completed:** 2026-04-15T12:15:21Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Anchored backend execution to `analysis_run_id` workspaces, persisted the same `run_workspace` payload into run and artifact metadata, and removed normal backend dependence on `chdir_repo_root()`.
- Migrated `main.py`, CLI guidance, and console digests to run-scoped workspace defaults and added a regression that proves those paths are used without cwd mutation.
- Wired Compose and operator docs to a shared `/var/lib/edgar/run_workspaces` root and documented shared `data/processed` and `data/artifacts` as legacy-only paths.

## Task Commits

Each task was committed atomically:

1. **Task 1: Anchor persisted backend runs to `analysis_run_id` workspaces and persist provenance without cwd mutation**
   `07501b4` (`feat`) persisted backend workspace provenance and no-cwd execution
2. **Task 2: Migrate `main.py`, CLI/demo guidance, and Compose/docs to the run-workspace default**
   `12f99ec` (`feat`) entrypoint migration and deployment/doc updates

## Files Created/Modified

- `backend/services/edgar_pipeline_execution_service.py` - Builds run workspaces from persisted run IDs, stores workspace provenance, and ingests artifacts with the same payload.
- `edgar_project/orchestration/agent.py` - Accepts `execution_context` so backend execution can pass the serialized workspace into orchestration.
- `tests/test_run_isolation_execution_service.py` - Proves backend execution uses explicit workspace paths, persists provenance, and does not call cwd-mutation helpers.
- `main.py` - Generates a run-scoped workspace under `data/runs/` and prints the resolved output paths.
- `edgar_project/cli.py` - Removes repo-root `chdir` behavior and updates user guidance to the run-scoped layout.
- `edgar_project/console_digest.py` - Detects run workspaces and reports them as the normal live-run output root.
- `docker-compose.yml` - Adds `EDGAR_BACKEND_RUN_WORKSPACE_ROOT` plus a shared `run_workspaces` volume for both `api` and `worker`.
- `docs/local-stack.md` and `data/README.md` - Document the shared run-workspace root and relabel shared processed/artifact directories as legacy-only defaults.
- `tests/test_run_isolation_entrypoints.py` - Adds CLI and `main.py` regression coverage for run-scoped workspaces and no-cwd execution.

## Decisions Made

- Reused the existing artifact-ingest metadata merge behavior instead of modifying `ArtifactService`, because it already preserved `source_path` while accepting the new `run_workspace` payload from the execution service.
- Used persisted `analysis_run_id` values as the canonical backend workspace IDs so stored metadata, durable directories, and artifact provenance all agree on one identity.
- Kept `manual_validation_csv` as an explicit shared input path inside the workspace payload rather than treating it as a copied workspace artifact.

## Deviations from Plan

None.

## Issues Encountered

None.

## User Setup Required

None - local Compose users automatically get the shared `run_workspaces` volume after recreating `api` and `worker`.

## Next Phase Readiness

- Overlap and explicit-path regression suites can now assert real backend provenance and no-cwd entrypoint behavior in Plan `01-04`.
- The documented runtime now points every normal execution path at run-scoped workspaces, so the remaining work is regression hardening rather than additional wiring.
- No blockers identified for the final Phase 1 plan.

## Self-Check: PASSED

- Summary file exists at `.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md`.
- Task commits verified in git history: `07501b4`, `12f99ec`.
- Verification passed: `python3 -m pytest tests/test_backend_foundation.py tests/test_run_isolation_execution_service.py -q` and `python3 -m pytest tests/test_run_isolation_entrypoints.py -q`.

---
*Phase: 01-run-isolation*
*Completed: 2026-04-15*
