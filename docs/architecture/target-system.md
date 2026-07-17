# Target System Architecture

Status: **design target — not yet implemented.** This describes the
input-agnostic, auditable agentic data-science platform the repository is being
migrated toward, and how each target component maps onto today's code
([`current-system.md`](./current-system.md)) with minimal disruption.

Guiding principle: **the LLM plans and interprets; deterministic code computes.**
Every material claim links to evidence; every experiment has typed inputs and
outputs; every run is reproducible from persisted structured state.

---

## 1. Target shape

The EDGAR-specific layers become one instance of a generic pattern. New/renamed
components are marked ✳; everything else is today's code, reused.

```
Frontend (investigation-oriented UI)  ← reuses chat shell + trace surfaces
        │
FastAPI /v1 (auth, ownership, runs, artifacts, evaluations)   ← unchanged
        │
Run driver  (generic; today EdgarPipelineExecutionService)    ← renamed/abstracted
        │
✳ Investigation engine  (iterative loop, replaces the fixed chain)
     ┌─────────────────────────────────────────────────────────────┐
     │  ✳ Planner        goal + state → next experiment(s)          │
     │  ✳ Experiment run typed inputs → deterministic tool          │
     │  ✳ Evidence updater  results → Evidence → Hypothesis status  │
     │  ✳ Critic         challenges evidence / competing explanations│
     │  ✳ Termination policy  sufficient / insufficient evidence     │
     │  ✳ Report synthesizer  evidence-linked narrative              │
     └─────────────────────────────────────────────────────────────┘
        │                                   │
✳ Deterministic tool registry        ✳ Input adapter registry
   (role-aware tools; EDGAR MCP          (AdapterRequest → DatasetManifest)
    tools are the first entries)          ├─ EDGAR adapter  → src/* (unchanged)
        │                                  └─ future adapters (CSV, warehouse, …)
   edgar_project/mcp + src/*  ← EDGAR computation preserved verbatim
        │
Artifact store + persistence (+ ✳ investigation_state table)  ← extends today's schema
        │
Evaluation framework  ← extended with adapter/agency cases (offline default preserved)
```

## 2. Target components → current code

| Target component | Realization | Reuses / replaces |
|---|---|---|
| **Input adapters** | `agentic/adapters` (`InputAdapter`, `AdapterRegistry`) | new seam; EDGAR adapter wraps `src`/`config` offline |
| **Dataset manifests** | `agentic/domain/manifest.py:DatasetManifest` | replaces raw `tickers` as the scope contract |
| **Investigation state** | `agentic/domain/investigation.py:InvestigationState` | aggregate root; persisted alongside `AnalysisRun` |
| **Hypotheses** | `agentic/domain/hypothesis.py:Hypothesis` | new first-class state |
| **Experiments** | `agentic/domain/experiment.py:Experiment` (+`ExperimentResult`) | typed wrapper over tool calls (today: `ToolCall`) |
| **Deterministic tools** | tool registry over `edgar_project/mcp/tools.py` | reuses `ToolResponseEnvelope`; adds role binding |
| **Planner** | generalized from `edgar_project/orchestration/planner.py` | goal+state → experiments (was one-shot template) |
| **Evidence updater** | new; maps `ExperimentResult` → `Evidence` → status | replaces "terminal snapshot only" |
| **Critic** | `backend/agents/critic_agent.py` over investigation state | reuse LLM + recorded model calls |
| **Termination policy** | new; emits `TerminationDecision` | replaces "chain finished" |
| **Report synthesizer** | `backend/agents/report_agent.py`, evidence-linked | reuse, require evidence refs |
| **Artifact store** | `backend/storage/*` | unchanged (already source-agnostic) |
| **Evaluation framework** | `edgar_project/evaluation/*` + new cases | offline `suite_fixtures_v1` preserved |
| **Investigation UI** | `frontend/*` new surfaces over investigation state | reuse chat + trace shells |
| **EDGAR demo adapter** | `agentic/adapters/edgar.py` + `edgar_project/demo` + CLI | EDGAR stays one-click demo |

## 3. Design invariants (enforced by `agentic/domain`)

1. **Typed, serializable state.** Every entity round-trips through
   `model_dump(mode="json")`. A run is reproducible from the persisted
   `InvestigationState`; no critical state lives only in model context.
2. **Explicit enums, not free-form strings** — `InvestigationStatus`,
   `HypothesisStatus`, `ExperimentStatus`, `EvidenceDirection`, `TerminationReason`.
3. **Claims link to evidence** — `Evidence` carries direction, strength, and
   verifiable `EvidenceRef` locators; the report synthesizer may only assert what
   evidence backs.
4. **Failure and uncertainty are valid outputs** — termination distinguishes
   `sufficient_evidence` from `insufficient_evidence`; hypotheses can be
   `supported`, `weakened`, `rejected`, `inconclusive`.
5. **Domain separate from persistence** — `agentic/domain` has no SQLAlchemy
   dependency; storage mapping is additive with a reversible migration.
6. **Offline-safe adapters** — `InputAdapter.build_manifest` never requires
   network, so deterministic fixture execution is always possible.
7. **No computation in prompts** — deterministic tools compute; the LLM selects
   and interprets.

## 4. Target execution path (input-agnostic)

1. User states a goal + selects an adapter (EDGAR by default) and scope.
2. `InputAdapter.build_manifest(AdapterRequest)` → `DatasetManifest` (columns typed
   by `ColumnRole`, entities, provenance).
3. `InvestigationState` is created with the goal + manifest; status `planning`.
4. **Loop** until the termination policy stops:
   a. Planner proposes the next `Experiment`(s) from goal + current state (open
      hypotheses, prior evidence).
   b. Experiment runs a deterministic tool (role-bound), producing a typed
      `ExperimentResult` + artifacts.
   c. Evidence updater turns results into `Evidence`, adjusting `Hypothesis.status`
      / `confidence` (support / weaken / reject).
   d. Critic optionally challenges evidence or proposes a competing explanation
      (which becomes another hypothesis/experiment).
   e. Termination policy records a `TerminationDecision` (stop on sufficient or
      insufficient evidence; else continue, bounded by max iterations).
5. Report synthesizer produces an evidence-linked narrative; artifacts ingested;
   `InvestigationState` + `AnalysisRun` persisted; UI renders from typed state.

EDGAR is this exact loop with the EDGAR adapter and the EDGAR deterministic tools;
a single-experiment "run the whole pipeline once" investigation reproduces today's
behavior byte-for-byte for the demo and regression fixtures.

## 5. What deliberately does NOT change

- The deterministic numerical layer (`src/*`) and its outputs/units.
- Auth, ownership, JWT-server-side model, artifact delivery, storage backends.
- Run lifecycle status machine and worker lease/finalize semantics (extended, not
  rewritten).
- Docker Compose topology (db / migrate / api / worker / web).
- The offline evaluation default (`suite_fixtures_v1`) and CLI demo entry points.

See [`migration-plan.md`](./migration-plan.md) for the staged path and
[`domain-boundaries.md`](./domain-boundaries.md) for the ownership rules that keep
these guarantees intact.
