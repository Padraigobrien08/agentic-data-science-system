# Phase 1: Run Isolation - Context

**Gathered:** 2026-04-15
**Status:** Ready for planning

<domain>
## Phase Boundary

Introduce explicit per-run workspaces and artifact-path contracts so every execution is isolated from other runs. This phase covers where run outputs live, how explicit paths flow through `src/`, `edgar_project/`, and `backend/`, and how the current shared Phase 1 paths are migrated without keeping them as the default execution behavior.

It does not include worker lease renewal, long-term retention policy, or remote object-storage rollout; those belong to later phases.

</domain>

<decisions>
## Implementation Decisions

### Workspace lifecycle
- **D-01:** Normal execution should use a durable per-run workspace on disk, not a temp-only workspace that disappears immediately after ingest.

### Legacy output compatibility
- **D-02:** Normal execution must stop writing automatically to shared `data/processed/*` and `data/artifacts/*` paths.
- **D-03:** Legacy Phase 1 global outputs may remain only as an explicit dev/legacy opt-in for local/manual workflows, never as the default or implicit behavior.
- **D-04:** Report generation and downstream artifact readers must consume explicit artifact paths end-to-end; default-path fallback is only acceptable inside the explicit legacy/dev mode.

### Run identity contract
- **D-05:** Backend, worker, CLI, and MCP flows should share one run-scoped workspace/artifact contract instead of mixing repo-global outputs with persisted per-run storage.
- **D-06:** When a persisted backend run exists, the workspace contract should anchor to that run identity; non-DB flows should generate a compatible run-scoped identity instead of falling back to repo-global filenames.

### the agent's Discretion
- Exact workspace root and folder naming scheme for run-scoped directories
- Exact CLI or config surface for enabling the legacy/dev compatibility mode
- Whether the migration uses a short-lived compatibility shim or an immediate cutover, as long as the default path is isolated

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope
- `.planning/PROJECT.md` — overall hardening intent, non-negotiables, and brownfield constraints
- `.planning/REQUIREMENTS.md` — `EXEC-01`, `EXEC-02`, and `EXEC-03` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 1 goal, plan slots, and success criteria

### Existing architecture and current risks
- `.planning/codebase/ARCHITECTURE.md` — current execution layering across `src/`, `edgar_project/`, and `backend`
- `.planning/codebase/CONCERNS.md` — documented artifact-collision, cwd, and default-path risks that this phase must address
- `.planning/codebase/STRUCTURE.md` — where execution-path changes land in the current repo layout

### Current runtime and data layout
- `docs/local-stack.md` — API/worker shared-storage expectations in the documented local stack
- `data/README.md` — current meaning of `data/raw`, `data/processed`, `data/artifacts`, and `data/evaluation`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/artifact_service.py` — already ingests on-disk outputs into per-run stored artifacts under analysis-run-scoped URIs
- `edgar_project/orchestration/schemas.py` and `edgar_project/orchestration/executor.py` — already carry `artifact_paths` as a role-to-path contract through orchestration output
- `src/pipeline_runner.py:phase1_paths()` — centralizes the current expected artifact-path map, making it a natural seam for introducing explicit run-scoped paths
- `tests/mcp/conftest.py` and `tests/mcp/test_tools.py` — already use temporary artifact paths, which can be extended into isolation-focused regression coverage

### Established Patterns
- `config.py` defines repo-global path constants and eagerly creates `data/raw`, `data/processed`, and `data/artifacts`
- `edgar_project/repo_layout.py` and `backend/services/edgar_pipeline_execution_service.py` currently rely on `ensure_repo_root_on_syspath()` and `chdir_repo_root()` to make those globals work
- `edgar_project/mcp/tools.py` supports `use_default_artifact_paths=True`, which is the current default-path escape hatch for report generation
- Backend persistence expects local files to exist first, then ingests them into managed storage rather than writing directly to storage

### Integration Points
- `src/pipeline_runner.py` — writer functions and the current Phase 1 artifact-path map
- `config.py` — current repo-global path roots that need to stop being the normal execution contract
- `edgar_project/mcp/adapters.py` and `edgar_project/mcp/tools.py` — bridge explicit paths versus default Phase 1 paths
- `backend/services/edgar_pipeline_execution_service.py` — current repo-root dependency and the ingest loop that consumes `out.artifact_paths`
- `edgar_project/cli.py` and `docs/local-stack.md` — user-facing execution paths and documented runtime assumptions that will need updated semantics

</code_context>

<specifics>
## Specific Ideas

- User agreed with the recommended defaults for all identified gray areas:
  - durable per-run workspaces
  - no normal automatic writes to shared `data/processed` / `data/artifacts`
  - default-path behavior only as explicit legacy/dev opt-in
  - one unified run-scoped workspace contract across backend, worker, CLI, and MCP

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 01-run-isolation*
*Context gathered: 2026-04-15*
