# Generalized Agentic Data-Science Architecture

This document tracks the transformation of the platform from an EDGAR-specific
analysis app into an **input-agnostic, auditable agentic data-science platform**.
EDGAR is preserved as (1) a one-click demo, (2) a first-party input adapter,
(3) a reference investigation template, and (4) a regression fixture.

The deterministic EDGAR computation layer under `src/` is not moved or bypassed.
The LLM plans and interprets; deterministic code computes.

## Target components

| Component | Status | Location |
|---|---|---|
| Input adapters | ✅ seam landed | `agentic/adapters/` |
| Dataset manifests | ✅ landed | `agentic/domain/manifest.py` |
| Investigation state | ✅ landed | `agentic/domain/investigation.py` |
| Hypotheses | ✅ landed | `agentic/domain/hypothesis.py` |
| Experiments (typed I/O) | ✅ landed | `agentic/domain/experiment.py` |
| Evidence | ✅ landed | `agentic/domain/evidence.py` |
| EDGAR demo adapter | ✅ landed | `agentic/adapters/edgar.py` |
| Deterministic tool registry | ⬜ planned | reuse `edgar_project/mcp/tools.py` behind a generic registry |
| Planner (goal → experiments) | ⬜ planned | generalize `edgar_project/orchestration/planner.py` |
| Evidence updater | ⬜ planned | maps experiment results → evidence → hypothesis status |
| Critic | ⬜ planned | reuse `backend/agents/critic_agent.py` over investigation state |
| Termination policy | ⬜ planned | `TerminationDecision` producer (sufficient/insufficient evidence) |
| Report synthesizer | ⬜ planned | evidence-linked; reuse `backend/agents/report_agent.py` |
| Artifact store | ✅ exists | `backend/storage/` (already source-agnostic) |
| Evaluation framework | ✅ exists | `edgar_project/evaluation/` (extend with adapter cases) |
| Investigation UI | ⬜ planned | `frontend/` surfaces over investigation state |
| Persistence mapping | ⬜ planned | map domain entities → `backend/models/` via a migration |

## Design invariants (enforced by the domain layer)

- **Typed, serializable state.** Every entity is a Pydantic model that
  round-trips through `model_dump(mode="json")`. A run is reproducible from the
  persisted `InvestigationState` aggregate; no critical state lives only in
  model context.
- **Explicit enums, not free-form strings.** Lifecycle values
  (`InvestigationStatus`, `HypothesisStatus`, `ExperimentStatus`,
  `EvidenceDirection`, `TerminationReason`) are enums.
- **Claims link to evidence.** `Evidence` carries a direction, a strength, and
  verifiable `EvidenceRef` locators; `InvestigationState.add_evidence`
  back-links evidence onto its hypotheses.
- **Failure and uncertainty are valid outputs.** `TerminationReason` includes
  both `sufficient_evidence` and `insufficient_evidence`; hypotheses can be
  `supported`, `weakened`, `rejected`, or `inconclusive`.
- **Domain separate from persistence.** `agentic/domain` has no SQLAlchemy
  dependency; storage mapping is a later, additive phase with a migration.
- **Offline-safe adapters.** `InputAdapter.build_manifest` must not require
  network access, so deterministic fixture execution is always possible. Live
  fetching stays in source-specific tooling (EDGAR MCP tools).

## The input-adapter seam

```
AdapterRequest ── InputAdapter.build_manifest ──▶ DatasetManifest
                        │                              │
                  (offline-safe)               columns typed by ColumnRole
                                                 (entity_id / time_index /
                                                  metric / dimension / ...)
```

Deterministic tools bind to columns by **role**, not by hard-coded EDGAR names,
so the same planner/experiment machinery works for any adapter that can emit a
manifest. `AdapterRegistry` selects an adapter by id at runtime and is
dependency-injectable (tests build their own empty registry).

The `EdgarInputAdapter` describes the SEC panel either from the pipeline's
`FEATURE_COLS` metric contract (declared schema, no data) or from a materialized
panel CSV (`parameters['panel_csv']`, columns/entities/row_count derived from the
file). It reuses `src`/`config` and adds no numerical computation of its own.

## How agency is expressed

Per the project's definition of agency, decisions are persisted structured state:

- execution paths vary by `InvestigationGoal`;
- experiments are selected dynamically and recorded as `Experiment` rows with
  typed inputs and typed `ExperimentResult` outputs;
- intermediate results become `Evidence` that moves `Hypothesis.status`/
  `confidence`, which in turn affects what runs next;
- the run stops via an explicit `TerminationDecision` for either sufficient or
  insufficient evidence.

## Phased roadmap

1. **Domain + adapter seam** (this change) — typed entities, manifest, registry,
   EDGAR adapter, tests. Additive; no existing surface changed.
2. **Deterministic tool registry** — wrap existing MCP tools as role-aware
   experiments callable from a generic registry.
3. **Generalized planner + evidence updater** — goal → experiments over a
   manifest; results → evidence → hypothesis status.
4. **Termination policy + evidence-linked report synthesizer.**
5. **Persistence mapping + migration** — store `InvestigationState` alongside the
   existing `AnalysisRun` model.
6. **Investigation UI + evaluation cases** for non-EDGAR adapters.

Each phase inspects first, extends rather than rewrites, adds tests, and keeps
the EDGAR demo and its regression tests green.
