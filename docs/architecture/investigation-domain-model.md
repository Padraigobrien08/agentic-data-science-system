# Investigation Domain Model

Status: **foundational domain model — implemented, not wired into production
orchestration.** This describes the framework-independent typed entities in
`agentic/domain/` that model an input-agnostic agentic data-science
investigation. It is the structured state a future agent loop reads and writes;
the loop itself is deliberately **not** built yet.

Companion docs: [`current-system.md`](./current-system.md),
[`target-system.md`](./target-system.md),
[`migration-plan.md`](./migration-plan.md),
[`domain-boundaries.md`](./domain-boundaries.md).

---

## 1. Entities and responsibilities

All entities inherit `DomainModel` (Pydantic, `extra="forbid"`, JSON-serializable)
and carry an explicit, type-prefixed, stable id (`new_id("hyp")` → `hyp_…`).

| # | Entity | File | Responsibility |
|---|---|---|---|
| 1 | `Investigation` | `investigation.py` | Durable root: identity + lifecycle `status` + the working `state`. Owns status transitions. |
| 2 | `InvestigationGoal` | `investigation.py` | The objective, adapter binding, success criteria, constraints, scope parameters. |
| 3 | `DatasetReference` | `manifest.py` | Stable pointer to a concrete dataset instance (locator + content hash), optionally embedding a manifest. |
| 4 | `DataSource` | `manifest.py` | A system data is acquired from (EDGAR is one), with adapter id and JSON-safe params. |
| 5 | `DatasetManifest` | `manifest.py` | Typed schema of a dataset; columns carry `ColumnRole` so tools bind by role, not by EDGAR names. |
| 6 | `Hypothesis` | `hypothesis.py` | A falsifiable claim; bounded `confidence`; status advanced by evidence via a validated graph. |
| 7 | `Evidence` | `evidence.py` | An interpreted observation bearing on hypotheses; explicit `direction` + bounded strength/reliability/coverage; verifiable refs. |
| 8 | `ExperimentDefinition` | `experiment.py` | Reusable template for a kind of experiment (tool, purpose, preconditions). |
| 9 | `ExperimentRequest` | `experiment.py` | A concrete planned experiment: typed params, target hypotheses, cost estimate, expected info gain, preconditions, reproducibility. |
| 10 | `ExperimentResult` | `experiment.py` | Typed outcome: observations, produced evidence ids, metrics, artifacts, error, reproducibility. |
| 11 | `Observation` | `observation.py` | A raw, pre-interpretation fact (value/outlier/gap) with a verifiable data reference. |
| 12 | `OpenQuestion` | `questions.py` | A tracked unresolved thread; makes "insufficient evidence" auditable. |
| 13 | `AgentDecision` | `decisions.py` | A recorded decision (which experiment/hypothesis and why) — agency as data. |
| 14 | `Critique` | `decisions.py` | An adversarial challenge to a hypothesis/evidence/conclusion, with type + severity. |
| 15 | `Conclusion` | `conclusion.py` | The current evidence-linked answer with a disposition (supported/refuted/inconclusive/insufficient). |
| 16 | `InvestigationState` | `investigation.py` | Serializable working memory: all of the above collections + confidence + budget + termination + version. |
| 17 | `TerminationDecision` | `investigation.py` | An explicit stop/continue decision; sufficient **and** insufficient evidence are valid reasons. |
| 18 | `ReproducibilityManifest` | `provenance.py` | Frozen context (code/tool/prompt versions, model config, seed, datasets, env) to reproduce a run. |

Supporting value objects: `Provenance` + `ProvenanceSource` (first-class,
required on every agent-produced entity), `ColumnSpec`, `SourceReference`,
`PayloadReference`, `Precondition`, `CostEstimate`, `ExperimentError`,
`EntityRef`, `BudgetState`, `ModelConfigSnapshot`, `EnvironmentInfo`.

### Reuse of existing concepts

The model deliberately mirrors patterns already in the codebase (see
[`current-system.md`](./current-system.md)):

- String-backed enums for storage portability (matches `backend/models/enums.py`,
  `edgar_project/orchestration/schemas.py`).
- Provenance fields `model_call_id` / `prompt_id` / `prompt_version` mirror
  `IntentAssistancePayload` and the `ModelCall` audit row.
- `ColumnRole`-typed manifests are the same seam the `agentic/adapters` EDGAR
  adapter already emits.
- Typed JSON params (`ExperimentParameters`) mirror the orchestration
  `PlannedStep.tool_input` / `ToolCallStep.params` contract.

## 2. State ownership

```
Investigation (root: id, status, timestamps)
└── InvestigationState (working memory; version)
     ├── objective: InvestigationGoal
     ├── datasets: [DatasetReference → DatasetManifest → ColumnSpec]
     ├── hypotheses: [Hypothesis] ── supporting/contradicting_evidence_ids ─┐
     ├── pending_experiments: [ExperimentRequest]                           │
     ├── completed/failed_experiments: [ExperimentResult → Observation]     │
     ├── evidence: [Evidence] ──────────────────────────────────────────────┘ (by hypothesis_ids + direction)
     ├── observations: [Observation]
     ├── open_questions / decisions / critiques
     ├── current_conclusion: Conclusion
     ├── confidence, budget: BudgetState, termination: TerminationDecision
```

- **`Investigation` owns lifecycle status**; only it may call `set_status`
  (validated against `ALLOWED_INVESTIGATION_TRANSITIONS`).
- **`InvestigationState` owns the collections and their linking.** Mutators like
  `add_evidence` link evidence onto hypotheses by `direction`;
  `record_experiment_result` files results and lifts observations into state and
  increments the budget. Callers never hand-maintain cross-links.
- **`Hypothesis` owns its own status/confidence** and enforces its transition
  graph (`ALLOWED_HYPOTHESIS_TRANSITIONS`); state never mutates a hypothesis'
  status behind its back.
- Cross-entity references are **ids** (or typed `EntityRef`), never nested object
  aliases, so the aggregate stays a clean serializable tree.

## 3. Persistence boundaries

- **No SQLAlchemy dependency.** `agentic/domain` imports only Pydantic + stdlib.
  Persistence models under `backend/models/` stay separate.
- **Mapping is a later, additive phase** (migration-plan Stage 5): an
  `investigation_states` table or typed JSON column linked 1:1 to `analysis_runs`,
  populated by a mapper module. Existing `output_payload_json` /
  `meta_json.ai_agents` remain for backward-compatible UI parsing.
- **Serialization contract:** every entity round-trips via
  `model_dump(mode="json")` / `model_validate` (datetimes as ISO-8601). This is
  the persistence and transport format; there is no hidden in-process state.
- **Two provenance concepts, on purpose:** `DatasetProvenance` captures *data
  lineage* (source, fetch time, request params); `Provenance` captures *decision
  lineage* (which agent/model/rule/tool produced an entity). They are not merged.

## 4. Lifecycle

Investigation status: `created → planning → running ⇄ awaiting_evidence →
{converged | exhausted | failed}` (terminal states have no outgoing edges).

Hypothesis status: `proposed → active → {supported ⇄ weakened, unresolved,
rejected}`; `rejected` is terminal; `supported`/`weakened`/`unresolved` may be
revisited as evidence changes.

Intended loop (built later, not now):

1. Build `InvestigationGoal`; select adapter; `build_manifest` → `DatasetReference`.
2. `Investigation.start(goal)`; `set_status(planning)`.
3. Planner proposes `Hypothesis` + `ExperimentRequest`; records `AgentDecision`.
4. `set_status(running)`; run the deterministic tool → `ExperimentResult`
   (`record_experiment_result`).
5. Evidence updater turns results into `Evidence` (`add_evidence`), moving
   hypothesis status/confidence; critic may add `Critique` / competing hypotheses.
6. Termination policy records a `TerminationDecision` (sufficient or insufficient);
   loop or stop, bounded by `BudgetState`.
7. Report synthesizer writes an evidence-linked `Conclusion`; `set_status(converged
   | exhausted)`.

## 5. Invariants

1. **Bounded confidence/quality.** `confidence`, `strength`, `reliability`,
   `coverage`, `expected_information_gain` ∈ [0, 1] (Pydantic-enforced).
2. **Provenance is first-class and required** on every agent-produced entity
   (`Hypothesis`, `Evidence`, `Observation`, experiments, decisions, critiques,
   conclusion). `TerminationDecision.provenance` is optional only for system stops.
3. **Explicit enums, never free strings**, for every status/type/direction.
4. **Stable explicit ids.** Type-prefixed, generated once, never reassigned;
   references use ids.
5. **Validated transitions.** Illegal hypothesis/investigation status changes
   raise `IllegalHypothesisTransition` / `IllegalInvestigationTransition`.
6. **Serializable and strict.** `extra="forbid"` everywhere; every entity
   round-trips through JSON.
7. **Claims link to evidence.** `Evidence` requires a `SourceReference`;
   `Conclusion` references hypotheses and key evidence by id.
8. **Failure/uncertainty are valid.** `insufficient_evidence`, `unresolved`,
   `inconclusive` are legal terminal states.
9. **Schema versioning.** `DOMAIN_SCHEMA_VERSION` plus per-entity `schema_version`
   / `InvestigationState.version`.
10. **Typed over generic.** Dict fields are used only where genuinely open (tool
    `parameters`, version maps); everything else is a typed model.

## 6. Extension points

- **New data sources** — add a `DataSource` kind + an input adapter that emits a
  `DatasetManifest`; the domain is unchanged.
- **New experiment types** — register an `ExperimentDefinition` over a
  deterministic tool; `ExperimentRequest.parameters` stays JSON-typed.
- **New evidence kinds** — extend `EvidenceType`; strength/reliability/coverage
  scoring is uniform.
- **New reasoning steps** — extend `DecisionType` / `CritiqueType`; decisions and
  critiques are open collections on the state.
- **New termination rules** — a policy produces `TerminationDecision`; the reason
  enum is the extension point.
- **Persistence** — implement a mapper `InvestigationState ⇄ rows` without
  touching the domain (Stage 5).
- **Bumping the contract** — raise `DOMAIN_SCHEMA_VERSION` and migrate on read.

## 7. Examples & tests

- `agentic/domain/examples.py` builds two fully-populated, valid investigations:
  `example_investigation()` (converged, sufficient evidence) and
  `example_inconclusive_investigation()` (exhausted, insufficient evidence).
- `tests/agentic/` covers validation (`test_domain_validation.py`), serialization
  round-trips (`test_domain_serialization.py`), state transitions
  (`test_domain_transitions.py`), and example consistency
  (`test_domain_examples.py`) — 33 tests, fully offline. Nothing is wired into
  the run path.
