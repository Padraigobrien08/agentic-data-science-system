# Phase 01: Run Isolation - Research

**Researched:** 2026-04-15
**Domain:** Run-scoped filesystem contracts for deterministic EDGAR execution
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
### Workspace lifecycle
- **D-01:** Normal execution should use a durable per-run workspace on disk, not a temp-only workspace that disappears immediately after ingest.

### Legacy output compatibility
- **D-02:** Normal execution must stop writing automatically to shared `data/processed/*` and `data/artifacts/*` paths.
- **D-03:** Legacy Phase 1 global outputs may remain only as an explicit dev/legacy opt-in for local/manual workflows, never as the default or implicit behavior.
- **D-04:** Report generation and downstream artifact readers must consume explicit artifact paths end-to-end; default-path fallback is only acceptable inside the explicit legacy/dev mode.

### Run identity contract
- **D-05:** Backend, worker, CLI, and MCP flows should share one run-scoped workspace/artifact contract instead of mixing repo-global outputs with persisted per-run storage.
- **D-06:** When a persisted backend run exists, the workspace contract should anchor to that run identity; non-DB flows should generate a compatible run-scoped identity instead of falling back to repo-global filenames.

### Claude's Discretion
- Exact workspace root and folder naming scheme for run-scoped directories
- Exact CLI or config surface for enabling the legacy/dev compatibility mode
- Whether the migration uses a short-lived compatibility shim or an immediate cutover, as long as the default path is isolated

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXEC-01 | User can run multiple analyses concurrently without one run overwriting another run's processed files or artifacts | Use one durable workspace root per run-scoped identity; make all writers derive paths from that contract instead of `config.DATA_PROCESSED` / `config.DATA_ARTIFACTS` |
| EXEC-02 | User can inspect a completed run and trust that every artifact and report was generated from that run's explicit input/output paths | Preserve explicit `artifact_paths`, persist workspace metadata, and remove implicit default-path reads from normal execution |
| EXEC-03 | Operator can rerun or resume a run without depending on process-global cwd changes or repo-root default artifact locations | Remove `chdir_repo_root()` from normal backend execution and pass explicit paths end-to-end through MCP/orchestration/backend |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Keep the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture; Phase 1 should harden current seams, not replace them.
- Prefer explicit seams and incremental migrations over invasive refactors; backend, worker, CLI, MCP, and frontend flows already exist and must keep working.
- Preserve the deterministic non-LLM analytical path in `src/`; run isolation must not bury or rewrite the numerical pipeline.
- Avoid breaking existing run APIs, artifact access patterns, and local development workflows unless a migration path is introduced.
- Defaults must be safe in deployed environments, but local/manual compatibility modes are acceptable when they are explicit opt-ins.
- Health, metrics, and retained run data must reflect real runtime state; false provenance is worse than noisy signals.
- Keep backend layering intact: path/build logic can be shared, but HTTP stays in `backend/api`, orchestration in `edgar_project/orchestration`, MCP boundaries in `edgar_project/mcp`, and deterministic file writers in `src/`.
- Use existing code conventions: package-root imports, typed Python interfaces, service-layer exceptions, and pytest as the backend validation surface.

## Summary

The repo already has half of the isolation story. At the persisted-storage layer, artifacts are already stored under run-scoped object keys such as `artifacts/analysis_runs/{analysis_run_id}/...` in `backend/services/artifact_service.py`. At the orchestration layer, `artifact_paths` is already a stable role-to-path map carried through `OrchestrationOutput`. The missing half is earlier in the flow: the deterministic pipeline still writes live outputs into repo-global `data/processed/*` and `data/artifacts/*`, `generate_report` still has a built-in default-path mode, the planner still selects that mode by default for granular plans, and backend execution still relies on `chdir_repo_root()` so those globals resolve.

Phase 1 should therefore be a contract refactor, not a storage rewrite. Introduce one run-scoped workspace contract, rooted at a durable directory per run identity, preserve the existing processed/artifacts directory split and existing basenames, and make every write and read path flow from that contract. Normal execution should never touch shared `data/processed` or `data/artifacts`. Those global paths can remain only behind an explicit dev/legacy mode.

The main planning trap is operational, not just code-level: the documented Compose stack shares only the managed artifact-storage volume, not a raw workspace volume. If the new workspace root lives on container-local `/app/data/...`, worker-written workspaces will not be durable across container restarts and will not be shared with other processes. The Phase 1 plan should therefore include a backend-configurable workspace root plus a Compose/docs update for a shared workspace volume.

**Primary recommendation:** Use a single run-scoped workspace contract rooted at `data/runs/<run_scoped_id>/` locally and a backend-configured shared root in API/worker deployments, then thread explicit `Path` values through `src/`, MCP, orchestration, and backend while demoting repo-global output paths to explicit legacy mode only.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Python stdlib (`pathlib`, `uuid`) | Python 3.12+ target; local shell is 3.11.0 | Build deterministic run workspace paths and compatible run-scoped IDs | No new dependency, already consistent with repo path handling and file I/O |
| Pydantic | 2.11.10 locally; repo standard is Pydantic 2 | Type the workspace/artifact contract where it crosses orchestration/backend boundaries | The repo already uses Pydantic for settings, orchestration contracts, and API schemas |
| pytest | 8.4.2 locally; repo requires `>=8.0` | Regression coverage for path propagation, overlap isolation, and no-cwd execution | Existing backend/orchestration validation framework |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy | 2.0.49 locally; repo standard is `>=2.0.36` | Persist workspace metadata on `AnalysisRun` / artifact metadata if needed | When provenance needs to survive process restarts and inspection via API |
| `pydantic-settings` | Repo standard | Add a backend workspace-root setting using the same env-driven pattern as artifact storage | For API/worker deployments that cannot rely on repo-local `data/runs` |
| structlog | 25.5.0 locally; repo standard is `>=24.4.0` | Emit run/workspace provenance in existing structured logs | When logging workspace root, legacy mode, or artifact counts during execution |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Shared run workspace builder + `Path` objects | Ad hoc string concatenation in each tool/service | Faster to write, but guarantees drift between writers/readers and breaks provenance |
| Durable per-run directories | `tempfile.TemporaryDirectory()` as the default | Automatic cleanup conflicts with D-01 and makes rerun/resume/durable inspection brittle |
| Separate workspace root setting/volume | Reusing repo-global `data/processed` and `data/artifacts` | Violates EXEC-01/02/03 directly |

**Installation:**
```bash
# No new packages recommended for Phase 1.
```

**Version verification:** No new package install is recommended for Phase 1. Verified locally: `pydantic 2.11.10`, `SQLAlchemy 2.0.49`, `pytest 8.4.2`, `structlog 25.5.0`. CI is pinned to Python 3.12 in `.github/workflows/ci.yml`; the local shell is Python 3.11.0, so final validation should use CI or the project container image for 3.12 parity.

## Architecture Patterns

### Recommended Project Structure
```text
data/
└── runs/
    └── <run_scoped_id>/
        ├── processed/          # panel.csv, features.csv
        └── artifacts/          # anomalies.csv, report.md, trust CSVs
```

For backend/worker deployments:

```text
<run_workspace_root>/
└── <analysis_run_id-or-generated-id>/
    ├── processed/
    └── artifacts/
```

### Pattern 1: Central Run Workspace Contract
**What:** Create one builder that returns all run-scoped output paths and any shared reference inputs the run depends on.

**When to use:** Every live execution path: backend synchronous execute, worker execute, CLI run/demo, MCP `run_pipeline`, and the granular planner path.

**Recommended shape:**
- `run_scoped_id`: `analysis_run_id` when a DB run exists; generated UUID for non-DB flows
- `root`
- `processed_dir`
- `artifacts_dir`
- `manual_validation_csv` as an explicit shared input path
- helpers for `phase1_paths()` / MCP-role maps derived from the workspace

**Example:**
```python
# Source pattern: src/pipeline_runner.py + backend/services/artifact_service.py
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RunWorkspace:
    run_scoped_id: str
    root: Path
    processed_dir: Path
    artifacts_dir: Path
    manual_validation_csv: Path

    def phase1_paths(self) -> dict[str, Path]:
        return {
            "panel": (self.processed_dir / "panel.csv").resolve(),
            "features": (self.processed_dir / "features.csv").resolve(),
            "anomalies": (self.artifacts_dir / "anomalies.csv").resolve(),
            "report": (self.artifacts_dir / "report.md").resolve(),
            "data_quality": (self.artifacts_dir / "data_quality_summary.csv").resolve(),
        }


def build_run_workspace(root: Path, run_scoped_id: str, manual_validation_csv: Path) -> RunWorkspace:
    ws_root = (root / run_scoped_id).resolve()
    return RunWorkspace(
        run_scoped_id=run_scoped_id,
        root=ws_root,
        processed_dir=ws_root / "processed",
        artifacts_dir=ws_root / "artifacts",
        manual_validation_csv=manual_validation_csv.resolve(),
    )
```

### Pattern 2: Compute First, Write Second, Ingest Third
**What:** Keep `run_pipeline_computation()` as the pure in-memory computation seam, then write explicit paths, then ingest written files into managed storage.

**When to use:** All backend and MCP flows that currently call `write_all_phase1_artifacts()`.

**Why:** This matches the current repo split and minimizes brownfield risk. The computation path stays deterministic; only the write contract changes.

**Example:**
```python
# Source pattern: src/pipeline_runner.py + backend/services/edgar_pipeline_execution_service.py
panel, feats, anom, md, dq_df, ex_df, peer_df, cave_long = run_pipeline_computation(
    tickers,
    refresh=refresh,
)
paths = write_all_phase1_artifacts(
    workspace=workspace,
    panel=panel,
    features=feats,
    anomalies=anom,
    report_markdown=md,
    data_quality=dq_df,
    exclusions=ex_df,
    peer_signals=peer_df,
    extraction_caveats_long=cave_long,
)
for role_key, path in role_key_to_mcp_artifacts(paths).items():
    artifact_service.ingest_pipeline_file(
        path,
        role_key=role_key,
        analysis_run_id=analysis_run_id,
        meta_json={"workspace_root": str(workspace.root)},
    )
```

### Pattern 3: Explicit Path Handoff Across MCP and Orchestration
**What:** Use explicit CSV path fields in MCP and orchestration normal flows; keep legacy fallback only behind explicit dev mode.

**When to use:** Especially for `generate_report`, because that is where the planner still relies on repo-global defaults today.

**Example:**
```python
# Source pattern: edgar_project/mcp/schemas.py
GenerateReportInput(
    anomalies_csv_path=str(workspace.artifacts_dir / "anomalies.csv"),
    features_csv_path=str(workspace.processed_dir / "features.csv"),
    use_default_artifact_paths=False,
)
```

### Pattern 4: Backend Workspace Root as Settings + Shared Volume
**What:** Introduce a backend setting such as `run_workspace_root: Path` alongside `artifact_storage_root`.

**When to use:** API/worker execution, especially in Compose or any multi-process deployment.

**Primary recommendation:**
- Local/manual default: repo `data/runs`
- Backend/worker deployment: `EDGAR_BACKEND_RUN_WORKSPACE_ROOT=/var/lib/edgar/run_workspaces`
- Compose: mount a shared `run_workspaces` volume into both `api` and `worker`

**Why:** `docker-compose.yml` currently shares only `/var/lib/edgar/artifacts`; that is not enough for durable raw workspaces.

### Anti-Patterns to Avoid
- **Smuggling workspace data through generic `context` blobs:** this is a first-class execution dependency; use a named field or a dedicated contract object.
- **Leaving `planner.py` on `use_default_artifact_paths=True`:** if the default plan still selects repo-global fallback, Phase 1 is not actually complete.
- **Mixing managed artifact storage with raw workspace semantics:** raw workspace files can live on the same volume if needed, but keep a separate root/prefix from `artifact_storage_root`.
- **Teaching readers to rediscover siblings by basename:** every reader should consume an explicit path or the shared workspace contract, never infer a sibling file from cwd.
- **Keeping static human-facing text that promises `data/processed` / `data/artifacts`:** report footers, console digests, CLI help, and docs must reflect the new contract.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Run-scoped filesystem naming | Independent path concatenation in every writer/tool | One central `RunWorkspace`/`phase1_paths(workspace)` builder | Prevents drift and guarantees that readers and writers agree |
| Artifact ownership persistence | A second custom DB mapping for workspace outputs | Existing `artifact_paths` + `ArtifactService.ingest_pipeline_file()` | The repo already has run-scoped managed storage and `source_path` metadata |
| Deployment-specific workspace discovery | Hardcoded `/app/...` or repo-relative assumptions in backend | `pydantic-settings` field for `run_workspace_root` | Matches existing backend config patterns and keeps API/worker symmetric |
| Test sandboxes | Custom temp-folder helpers | Pytest `tmp_path` and existing monkeypatch patterns | Already used in MCP/pipeline tests and maps cleanly to path-injection work |
| Provenance display | Implicit “these files must live next to each other” logic | Persisted workspace metadata + explicit `artifact_paths` | Required to satisfy EXEC-02 without ambiguous fallbacks |

**Key insight:** the repo already solved post-ingest run isolation; Phase 1 should reuse that and stop the pre-ingest pipeline from writing to shared global locations.

## Common Pitfalls

### Pitfall 1: Default-Path Mode Survives the Cutover
**What goes wrong:** The planner or MCP tools still invoke `generate_report` with `use_default_artifact_paths=True`, so the report step quietly reads shared repo-global files.
**Why it happens:** The granular planner currently hardcodes that flag.
**How to avoid:** Make explicit path mode the only normal orchestration path; keep legacy mode behind a distinct CLI/config switch.
**Warning signs:** A passing report test still works when `artifact_paths` are empty or when no workspace is provided.

### Pitfall 2: Writers Are Refactored, Readers Are Not
**What goes wrong:** `write_all_phase1_artifacts()` starts writing into run-scoped paths, but report credibility helpers, manual validation, console digests, or docs still assume `data/processed` / `data/artifacts`.
**Why it happens:** There are many human-facing path strings outside the core writer functions.
**How to avoid:** Audit all consumers of `config.DATA_PROCESSED`, `config.DATA_ARTIFACTS`, `phase1_paths()`, and static `data/artifacts/...` strings.
**Warning signs:** Reports mention global paths while API artifacts resolve elsewhere.

### Pitfall 3: Container-Local Workspaces Masquerade as Durable Storage
**What goes wrong:** Backend/worker store workspaces under `/app/data/runs`, which is writable but not shared or durable in the documented Compose stack.
**Why it happens:** The current stack only mounts the managed artifact-storage volume.
**How to avoid:** Add a shared workspace-root setting and mount it into both containers.
**Warning signs:** A worker-generated run cannot be resumed after container recreation, or API and worker disagree on which files exist.

### Pitfall 4: Overloading `run_id` Instead of Separating Correlation and Workspace Identity
**What goes wrong:** The orchestration `run_id` becomes an implicit filesystem identifier and leaks into places that should be tied to the persisted `analysis_run_id`.
**Why it happens:** `AnalysisAgent` currently generates `run_id` internally.
**How to avoid:** Preserve orchestration `run_id` for correlation if needed, but introduce explicit `workspace_id` / workspace metadata rooted in `analysis_run_id` when a DB run exists.
**Warning signs:** Retries/resumes unexpectedly create new workspaces or orphan provenance records.

### Pitfall 5: Phase 1 Stops at File Paths and Misses Provenance
**What goes wrong:** Files become isolated, but the completed run record still does not make it easy to prove which workspace generated them.
**Why it happens:** It is tempting to rely on `artifact_paths` alone.
**How to avoid:** Persist workspace metadata on the run and, when ingesting files, preserve `source_path` plus workspace info in artifact metadata.
**Warning signs:** Operators can download stored artifacts but cannot answer “which on-disk workspace produced this?”

## Code Examples

Verified repo-aligned patterns to reuse:

### Centralized Artifact-Path Registry
```python
# Source: src/pipeline_runner.py
def phase1_paths() -> dict[str, Path]:
    art = config.DATA_ARTIFACTS
    return {
        "panel": (config.DATA_PROCESSED / "panel.csv").resolve(),
        "features": (config.DATA_PROCESSED / "features.csv").resolve(),
        "anomalies": (art / "anomalies.csv").resolve(),
        "report": (art / "report.md").resolve(),
    }
```

**Use in Phase 1:** keep the registry idea, but make it `phase1_paths(workspace)` so no normal call path depends on repo-global constants.

### Managed Artifact Ingestion Already Preserves Source Path
```python
# Source: backend/services/artifact_service.py
path = Path(source_path).expanduser().resolve()
if not path.is_file():
    raise FileNotFoundError(str(path))

if meta_json is None:
    merged_meta = {"source_path": str(path)}
elif isinstance(meta_json, dict):
    merged_meta = {**meta_json, "source_path": str(path)}
```

**Use in Phase 1:** add workspace metadata here instead of inventing a second provenance store.

### Tests Already Patch Paths Instead of Assuming Globals
```python
# Source: tests/test_metric_coverage.py
monkeypatch.setattr(config, "DATA_ARTIFACTS", tmp_path)
monkeypatch.setattr(config, "DATA_PROCESSED", tmp_path)
paths = write_all_phase1_artifacts(...)
```

**Use in Phase 1:** expand this into first-class workspace fixtures and overlapping-run regression tests.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Repo-global writes to `config.DATA_PROCESSED` / `config.DATA_ARTIFACTS` | Per-run workspace root with preserved `processed/` and `artifacts/` subdirs | Phase 1 target | Eliminates cross-run overwrite risk |
| `generate_report` reads defaults via `use_default_artifact_paths=True` | Normal flow passes explicit `features_csv_path` and `anomalies_csv_path`; legacy mode is opt-in only | Phase 1 target | Makes report provenance auditable |
| Backend executes after `chdir_repo_root()` | Backend executes from explicit workspace paths without cwd mutation | Phase 1 target | Supports rerun/resume and worker symmetry |
| Compose shares only managed artifact storage | Compose also shares a durable workspace root | Phase 1 target | Keeps workspaces durable in the documented stack |

**Deprecated/outdated:**
- Repo-global `phase1_paths()` as the normal live execution contract
- Planner defaulting to `use_default_artifact_paths=True`
- Human-facing guidance that “live runs write under `data/processed/` and `data/artifacts/`” without qualification

## Open Questions

1. **Should Phase 1 expose `workspace_root` as a public API field immediately?**
   - What we know: `artifact_paths` already exists and is the current public path contract.
   - What's unclear: whether any current UI/API consumer needs a first-class workspace-root field now.
   - Recommendation: keep public response compatibility; persist workspace metadata in `output_payload_json` or `meta_json` first, then add an API field only if the UI needs it.

2. **Should backend workspaces use a new volume or a separate prefix under the artifact-storage volume?**
   - What we know: the documented stack needs a shared durable filesystem root for raw run workspaces.
   - What's unclear: whether operations prefers one named volume or a shared volume with separate prefixes.
   - Recommendation: prefer a separate `run_workspaces` setting and volume for clarity; use a separate prefix under the existing volume only if minimizing Compose churn matters more than operational separation.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend execution/tests | ✓ | 3.11.0 locally | Use CI / backend container for Python 3.12 parity |
| pytest | Backend validation | ✓ | 8.4.2 | — |
| Docker | Compose/shared-volume validation | ✓ | 29.3.1 | Manual API + worker processes |
| Docker Compose | Validating shared workspace mounts in the documented stack | ✓ | v5.1.1 | Manual API + worker processes |

**Missing dependencies with no fallback:**
- None

**Missing dependencies with fallback:**
- Python 3.12 is not installed in the local shell; repo CI and containerized backend provide the required runtime.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.4.2 locally (`pytest>=8.0` in repo) |
| Config file | `pytest.ini` |
| Quick run command | `python3 -m pytest tests/mcp/test_tools.py tests/test_mcp_orchestration_artifact_contract.py tests/orchestration/test_phase3_orchestration.py -q` |
| Full suite command | `python3 -m pytest tests/ -q --tb=short` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-01 | Two overlapping runs write to distinct processed/artifact trees and keep distinct `artifact_paths` | integration | `python3 -m pytest tests/test_run_isolation_overlap.py::test_overlapping_runs_keep_distinct_artifact_paths -q` | ❌ Wave 0 |
| EXEC-02 | Completed run metadata and stored artifacts point back to explicit run-scoped source paths | unit/integration | `python3 -m pytest tests/test_run_isolation_workspace.py::test_workspace_paths_are_persisted_and_run_scoped -q` | ❌ Wave 0 |
| EXEC-03 | Backend/worker/CLI execution does not require repo-root cwd mutation or implicit Phase 1 defaults | unit | `python3 -m pytest tests/test_run_isolation_execution_service.py::test_execute_analysis_run_uses_explicit_workspace_paths -q` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `python3 -m pytest tests/test_run_isolation_workspace.py -q`
- **Per wave merge:** `python3 -m pytest tests/test_run_isolation_workspace.py tests/test_run_isolation_overlap.py tests/test_run_isolation_execution_service.py tests/mcp/test_tools.py tests/test_mcp_orchestration_artifact_contract.py tests/orchestration/test_phase3_orchestration.py -q`
- **Phase gate:** `python3 -m pytest tests/ -q --tb=short`

### Wave 0 Gaps
- [ ] `tests/test_run_isolation_workspace.py` — shared contract builder, explicit path registry, report/footer provenance expectations
- [ ] `tests/test_run_isolation_overlap.py` — overlapping run workspaces and artifact non-collision
- [ ] `tests/test_run_isolation_execution_service.py` — backend execution without `chdir_repo_root()` and with persisted workspace metadata

## Sources

### Primary (HIGH confidence)
- Local repo: `.planning/phases/01-run-isolation/01-CONTEXT.md`
- Local repo: `.planning/REQUIREMENTS.md`
- Local repo: `CLAUDE.md`
- Local repo: `src/pipeline_runner.py`
- Local repo: `src/report.py`
- Local repo: `src/manual_validation.py`
- Local repo: `edgar_project/mcp/schemas.py`
- Local repo: `edgar_project/mcp/tools.py`
- Local repo: `edgar_project/orchestration/planner.py`
- Local repo: `edgar_project/orchestration/execution_contract.py`
- Local repo: `backend/services/edgar_pipeline_execution_service.py`
- Local repo: `backend/services/artifact_service.py`
- Local repo: `backend/config/settings.py`
- Local repo: `docs/local-stack.md`
- Local repo: `docker-compose.yml`
- Local repo: `tests/mcp/conftest.py`, `tests/mcp/test_tools.py`, `tests/test_metric_coverage.py`, `tests/test_mcp_orchestration_artifact_contract.py`, `tests/orchestration/test_phase3_orchestration.py`
- Python docs: https://docs.python.org/3/library/pathlib.html
- Python docs: https://docs.python.org/3/library/tempfile.html
- Pydantic Settings docs: https://docs.pydantic.dev/latest/concepts/pydantic_settings/

### Secondary (MEDIUM confidence)
- None

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependency is recommended; the approach reuses repo-standard Python/Pydantic/pytest patterns
- Architecture: MEDIUM — the code seams are clear, but the exact public-vs-internal exposure of workspace metadata is still a planner decision
- Pitfalls: HIGH — each major risk is directly evidenced by current code paths and deployment docs

**Research date:** 2026-04-15
**Valid until:** 2026-05-15
