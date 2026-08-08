# Phase 33: Multi-Metric Investigations - Context

**Gathered:** 2026-08-07
**Status:** Ready for planning

<domain>
## Phase Boundary

An investigation can examine exactly one metric. Ask "is revenue growth slowing **and** is margin
quality deteriorating?" and the loop generates both hypotheses, investigates the first, and
strands the second at `proposed` forever — however well the agent reasons. Verified in phase
32-02: `[(['revenue_growth_pct'], 'supported'), (['margin_pct'], 'proposed')]`.

This phase lifts that. It is a product constraint first — multi-part questions are ordinary
analyst questions — and a benchmark constraint second: 32-02 had to drop a planned
`generate_hypotheses` case because no policy, however good, could pass it.

Out of scope: new experiment tools, new adapters, the nine `AgencyProperty` definitions, and the
frozen core tier's *result*. This phase changes how the loop plans, not what it can compute.

</domain>

<decisions>
## Implementation Decisions

### The constraint is narrower than it appears
- **D-01:** The domain model is already multi-metric. `Hypothesis.metric_refs` exists,
  `EvidenceUpdater` attaches evidence to `request.target_hypothesis_ids[0]`, and
  `HypothesisRow.metric_refs_json` persists it. **No migration is required.**
- **D-02:** The constraint lives in exactly two places in `InvestigationPlanner`:
  `_params_for(tool, interpretation, manifest)` reads `interpretation.metric_hint` — a single
  global hint — and `_target_hypothesis` returns the *first* matching open hypothesis rather than
  serving each in turn. Fix those and the rest of the loop already works per-hypothesis.
- **D-03:** Parameterise from the **target hypothesis's** metric, falling back to the
  interpretation hint, then `metrics[0]`. The planner already picks a target; it should use that
  target's metric.

### The published result must not move
- **D-04:** The core tier's 13/13 and the model's core 100% are **published artifacts**
  (`docs/agent/agency-scoreboard.md`, `data/evaluation/agency/scoreboard-2026-08-07*.json`).
  A single-hypothesis investigation must come out **byte-identical** — same tools, same order,
  same ids, same conclusion — or the published scoreboard silently becomes wrong.
- **D-05:** That equivalence is a test, not a hope. Assert it over the whole core tier before
  any multi-hypothesis behaviour is added.

### Semantics that have to be decided, not defaulted
- **D-06:** **Termination.** `TerminationPolicy.decide` currently returns `sufficient_evidence`
  as soon as *one* hypothesis is supported and challenged. With several claims live that strands
  the rest — the same bug in a new place. Sufficiency must mean every hypothesis has reached a
  terminal status, or the budget stopped the run.
- **D-07:** **Conclusion.** `ConclusionSynthesizer` takes `if supported: disposition = supported`,
  so one supported and one refuted claim reports as *supported* and the refutation disappears
  from the headline. A mixed outcome needs its own disposition rather than being rounded to the
  good news.
- **D-08:** **Budget.** Experiments scale with hypothesis count. `LoopBudget.max_experiments`
  defaults to 8; two claims at three tools each is 6, three claims is 9. The default must be
  reconsidered against the new shape rather than left to silently truncate multi-part
  investigations into `budget_exhausted`.

### the agent's Discretion
- Exact signature of the per-hypothesis parameterisation
- Whether candidates interleave across hypotheses or complete one before the next, as long as
  ordering is deterministic and resumable
- Exact name and confidence of the mixed disposition
- Whether the budget default changes or the loop scales it by hypothesis count

</decisions>

<specifics>
## Specific Ideas

The two-metric tools are already an exception worth studying: `fit_simple_regression` takes
`metrics[0], metrics[1]` and `analyze_correlation` takes no params at all. Whatever the new
parameterisation looks like, it has to leave those working — they are the existing proof that
the tool layer is not the thing constraining this.

`_target_hypothesis` returning "first open hypothesis whose `metric_refs` match, else the first
hypothesis at all" is doing double duty: it selects a target *and* silently makes the loop
single-claim. Splitting those two jobs is most of the change.

Watch the determinism guarantee. Ids are `idgen.make("exp", n + len(out))` and the batch
executor folds results in selection order precisely so state is a pure function of the run.
Iterating hypotheses must not make ordering depend on dict iteration or set ordering.

Resumability: `InvestigationLoop.resume` rebuilds `tracker.experiments_used` from persisted
completed + failed experiments. Multi-hypothesis runs are longer and therefore more likely to be
resumed mid-flight, so the resume path deserves an explicit multi-claim test rather than
inheriting coverage.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The constraint
- `agentic/agent/components.py` — `InvestigationPlanner._params_for` and `_target_hypothesis`
  are the two places to change; `ExperimentSelector`, `EvidenceUpdater`, `HypothesisUpdater`,
  `TerminationPolicy`, `ConclusionSynthesizer` are the downstream consumers
- `agentic/domain/hypothesis.py` — `metric_refs`, already per-hypothesis
- `agentic/domain/investigation.py` — `open_hypotheses()`, `find_hypothesis`

### What must not move
- `docs/agent/agency-scoreboard.md` — the published measurement this phase must not invalidate
- `agentic/evaluation/cases.py` — `SUITE_V1_CASES`, frozen
- `agentic/evaluation/baselines/fixture_floors.json` — core floors and the hard ceiling
- `.planning/phases/32-agency-suite-hardening/32-agency-suite-hardening-02-SUMMARY.md` — the
  probe that established the limitation, and the case that had to be dropped

### Behaviour that depends on planning order
- `agentic/agent/loop.py` — `_run_batch` folds outcomes in selection order for determinism
- `agentic/agent/ids.py` — `DeterministicIds`
- `agentic/agent/replay.py`, `agentic/agent/diff.py` — a changed path shows up as a diff
- `tests/agentic/test_parallel_experiments.py` — batching, ordering, resume invariants

### Persistence (read to confirm no migration, not to change)
- `backend/models/investigation_entities.py` — `HypothesisRow.metric_refs_json` already exists
- `backend/services/investigation_store.py`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Evidence is already attached per hypothesis via `request.target_hypothesis_ids`, so once
  experiments are parameterised per claim the evidence and hypothesis updaters need no change.
- `ConclusionSynthesizer` already collects `supported` / `rejected` / `weakened` as *lists* and
  joins their statements — it was written for several claims and only its disposition branch
  assumes one matters.
- `HypothesisRow.metric_refs_json` is persisted today, so a multi-claim investigation
  round-trips through the store without schema work.

### Established Patterns
- Components are small, single-purpose, and injected into `InvestigationLoop`; changes belong
  in a component, not in the loop body.
- Determinism is a load-bearing property, asserted by tests rather than assumed.
- Budgets bound the run and every terminal state is a typed `TerminationReason`.

### Integration Points
- `InvestigationPlanner._params_for` / `_target_hypothesis` — the change
- `TerminationPolicy.decide` — sufficiency across several claims
- `ConclusionSynthesizer.synthesize` — a mixed disposition
- `agentic/agent/budget.py` — `max_experiments` default
- `agentic/evaluation/cases.py` — the previously-unwinnable case, once it is winnable

### Known Risk
- **The published scoreboard is the thing most likely to break silently.** A planning change
  that reorders candidates alters tool paths, which alters ids, which alters diffs — and the
  core tier could still score 13/13 while no longer being the same investigation. Equivalence
  must be asserted on the *path*, not only on the pass rate.

</code_context>

<deferred>
## Deferred Ideas

- Cross-metric hypotheses ("does margin explain revenue?") — that is a relationship claim, not
  two independent claims, and needs different tool parameterisation
- Automatic budget scaling by hypothesis count, if a fixed default proves sufficient
- Re-measuring other models on the widened suite
- `ModelCall` persistence for agentic policy calls (from 31-01)
- Cached-input pricing tier (from 31-03)

</deferred>

---

*Phase: 33-multi-metric-investigations*
*Context gathered: 2026-08-07*
