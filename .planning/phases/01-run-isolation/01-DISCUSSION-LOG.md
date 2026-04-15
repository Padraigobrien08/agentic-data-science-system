# Phase 1: Run Isolation - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 1-Run Isolation
**Areas discussed:** Workspace visibility, Legacy path compatibility, Default-path fallbacks, Run identity contract

---

## Workspace visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Durable per-run workspace | Each run gets its own folder that remains on disk until cleanup | ✓ |
| Ephemeral workspace | Run in a temp directory, ingest outputs, then delete local files | |
| Hybrid | Durable workspaces for backend and worker runs, ephemeral for local CLI/demo runs | |

**User's choice:** Durable per-run workspace
**Notes:** User replied "Agree with all," which I interpreted as accepting the recommended option for this area and the other discussed areas.

---

## Legacy path compatibility

| Option | Description | Selected |
|--------|-------------|----------|
| Keep shared Phase 1 paths as the default | Continue writing normal runs to `data/processed` and `data/artifacts` | |
| Dual-write during normal execution | Write both run-scoped outputs and shared Phase 1 outputs by default during transition | |
| Remove automatic shared writes from normal execution | Normal runs use run-scoped outputs only; any shared-path mode must be explicit | ✓ |

**User's choice:** Remove automatic shared writes from normal execution
**Notes:** The shared Phase 1 paths are the current collision source, so the default execution path should stop using them.

---

## Default-path fallbacks

| Option | Description | Selected |
|--------|-------------|----------|
| Keep fallback behavior as the normal default | Continue relying on implicit `phase1_paths()` and `use_default_artifact_paths` in standard flows | |
| Explicit legacy/dev opt-in only | Keep fallback behavior only behind an explicit compatibility mode | ✓ |
| Delete all fallback behavior immediately | Remove all default-path support with no compatibility mode | |

**User's choice:** Explicit legacy/dev opt-in only
**Notes:** This keeps local/manual compatibility available without preserving the unsafe default.

---

## Run identity contract

| Option | Description | Selected |
|--------|-------------|----------|
| Mixed contracts by surface | Backend uses persisted run IDs, while CLI and MCP keep repo-global output semantics | |
| Orchestration run ID as the only anchor | All paths derive strictly from orchestration-level run identity | |
| One run-scoped contract across all surfaces | Backend, worker, CLI, and MCP all use compatible run-scoped workspace semantics | ✓ |

**User's choice:** One run-scoped contract across all surfaces
**Notes:** Exact non-DB ID generation can remain implementation detail, but repo-global filenames should no longer be the fallback contract.

---

## the agent's Discretion

- Exact workspace directory naming scheme
- Exact legacy/dev opt-in surface and migration shim details

## Deferred Ideas

None.
