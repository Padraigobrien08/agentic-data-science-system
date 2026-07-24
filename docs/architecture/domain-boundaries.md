# Domain Boundaries & Module Classification

Status: **analysis only.** Defines which modules are reusable as-is, reusable
behind an interface, EDGAR-specific (preserve as first-party adapter),
orchestration-specific, or candidates for deprecation — plus the ownership rules
that keep the preservation guarantees in
[`migration-plan.md`](./migration-plan.md) intact.

References: [`current-system.md`](./current-system.md),
[`target-system.md`](./target-system.md).

---

## 1. Classification

### A. Reusable unchanged (source-agnostic today)

| Module / area | Why it's already generic |
|---|---|
| `backend/auth`, `backend/security`, `backend/api/auth_deps.py`, `access_checks.py` | Identity/ownership; no EDGAR concepts |
| `backend/db/*` | Session/engine/base; domain-neutral |
| `backend/storage/*` (local, s3, resolver, factory) | Bytes keyed by `storage_uri`; no domain shape |
| `backend/observability/*` | Logging, tracing, metrics, middleware |
| `backend/worker/*` (loop, lease, failure_classification) | Queue/lease/retry over any run |
| `backend/services/{run_lifecycle,run_queue,artifact_service,artifact_delivery,user_service}` | Lifecycle/queue/delivery independent of pipeline |
| `backend/models/{user,project,artifact,model_call,run_execution_job}` | Generic (see §3 for `project.tickers` caveat) |
| `backend/repositories/*` | Thin persistence wrappers |
| `backend/domain/{status_transitions,run_progress,json_merge}` | Generic state helpers |
| `agentic/*` (new) | Purpose-built input-agnostic core |

### B. Reusable behind an interface (generalize, don't rewrite)

| Module | Interface to introduce | Note |
|---|---|---|
| `backend/services/edgar_pipeline_execution_service.py` | rename → generic run driver; keep alias | EDGAR-named but is the shared API+worker run path |
| `backend/agents/traceable_analysis_pipeline.py` | flag-gated investigation engine | fixed chain → iterative loop (off-path == today) |
| `backend/agents/critic_agent.py`, `report_agent.py` | operate over `InvestigationState` | reuse LLM + recorded model calls |
| `backend/agents/{intent_agent,planning_agent,intent_preferences_assistant}` | plug into generalized planner | keep deterministic-first stance |
| `edgar_project/mcp/schemas.py:ToolResponseEnvelope` | tool contract for the registry | already status/data/artifacts/errors |
| `backend/models/{analysis_run,run_step,tool_call}` | input-agnostic once counters/`tickers` are generic | additive columns only |
| `edgar_project/evaluation/*` | add adapter/agency cases | keep offline default suite |

### C. EDGAR-specific — **preserve as first-party adapter + reference template**

| Module | Role after migration |
|---|---|
| `src/*` (all: data_fetch, normalization, features, anomaly, peer_signals, trend_breaks, findings, report, pipeline_runner, metric_*, data_quality, exclusions, manual_validation) | Frozen deterministic computation behind the EDGAR adapter/tools |
| `config.py`, `main.py` | EDGAR defaults + repo-root Phase-1 entry |
| `edgar_project/mcp/{adapters,tools}.py` | EDGAR tool implementations (first registry entries) |
| `edgar_project/demo/*`, `edgar_project/run_workspace.py`, `edgar_project/repo_layout.py` | Demo + run-scoped workspace plumbing |
| `validation/manual_validation.csv`, `edgar_project/evaluation/fixtures/*` | EDGAR fixtures / goldens (regression) |
| `agentic/adapters/edgar.py` (new) | The adapter that keeps all of the above reachable, offline |

**Rule:** none of these are deleted or bypassed; they become the EDGAR instance of
the generic pattern and remain the one-click demo.

### D. Orchestration-specific

| Module | Disposition |
|---|---|
| `edgar_project/orchestration/planner.py`, `plan_templates.py`, `intent.py`, `goal_preferences.py`, `params.py`, `prompt_scope.py` | Generalize planning to goal+state→experiments; EDGAR templates become one adapter's plan library |
| `edgar_project/orchestration/executor.py` | Its `_dispatch_mcp` becomes the tool registry's EDGAR dispatch |
| `edgar_project/orchestration/{schemas,state,execution_contract}.py` | EDGAR vocabulary (tickers, InterpretedGoalCode, ResolvedCompany) → superseded by `agentic/domain` for new work; kept for the EDGAR path + back-compat |
| `edgar_project/orchestration/agent.py` | Coordinator seam; reused as the EDGAR single-experiment path |

### E. Deprecate / consolidate

| Item | Action |
|---|---|
| `orchestration/agent.py` (top-level wrapper) | Fold into `edgar_project.orchestration`; keep a shim only if imported |
| `tmp_empty_uf.csv` (repo root) | Remove (stray test artifact) — separate housekeeping change |
| `frontend/pnpm-lock.yaml` | Remove; repo standardizes on npm (`package-lock.json`) — housekeeping |

> Deprecations are **not** part of the functional migration and should land as
> isolated housekeeping commits so they never mix with behavior changes.

---

## 2. Boundary ownership rules

1. **Deterministic vs LLM.** `src/*` and registered tools compute; agents/planner
   only select and interpret. No numeric logic in prompts. (Enforced by keeping
   `src/*` frozen and covered by numerical regression tests.)
2. **Domain vs persistence.** `agentic/domain` never imports SQLAlchemy;
   persistence mapping lives in a mapper module + Alembic migration. Persistence
   models never leak into the investigation engine's core logic.
3. **Adapters own data acquisition.** Data enters only through an `InputAdapter`
   producing a `DatasetManifest`; the EDGAR bridge (`mcp/adapters.py` → `src`) is
   one adapter, invoked offline for manifests and via MCP tools for computation.
4. **Tools bind by role, not by EDGAR column names.** Experiments select tools by
   `ColumnRole` on the manifest, so the same engine runs any adapter's data.
5. **API is the only trust boundary the frontend crosses.** Ownership/auth stay in
   `backend/api`; the engine never re-implements them.
6. **Artifacts stay opaque.** Only `storage_uri`-referenced bytes cross to the
   browser, via `storage/resolver`; no raw paths.

---

## 3. EDGAR-shaped leakage to unwind (additively)

These are the concrete couplings that make the schema/contract EDGAR-biased.
Each is unwound by **adding** a generic form, not removing the EDGAR one:

- `Project.tickers` (JSON column) → generic `scope`/adapter parameters; keep
  `tickers` populated for EDGAR.
- `AnalysisRunCreate` / `OrchestrationInput.tickers` → optional `adapter_id` +
  `dataset_manifest`; `tickers` remains an EDGAR convenience.
- `ToolCall.{panel_row_count,feature_row_count,anomaly_count,report_character_count}`
  → generic `result_metrics_json` (additive); EDGAR keeps writing the named columns.
- `meta_json.ai_agents` / `output_payload_json` (untyped) → typed
  `InvestigationState` persistence; keep the JSON populated for the current UI
  parsers until the UI migrates.
- Naming: `EdgarPipelineExecutionService`, `run_traceable_edgar_pipeline` →
  generic names with back-compat aliases.

---

## 4. Dependency direction rules (target)

Allowed import direction (may not be violated):

```
frontend → api → services → repositories → models → db
services → investigation engine → { tool registry, adapter registry, agentic.domain }
tool registry → edgar_project.mcp.tools → edgar_project.mcp.adapters → src/*   (EDGAR only)
adapter registry → agentic.adapters.* (EDGAR adapter → src/* offline)
agentic.domain → (nothing app-specific; pure typed models)
evaluation → { src/*, investigation engine (mocked), models }
```

- `agentic.domain` depends on **nothing** in `backend/` or `edgar_project/`.
- The investigation engine depends on `agentic.domain` + registries, **not** on
  `src/*` directly.
- `src/*` never imports upward (backend/orchestration/agentic).

Keeping these directions is what lets EDGAR stay a swappable first-party adapter
while the generic engine, persistence, and UI evolve around it.
