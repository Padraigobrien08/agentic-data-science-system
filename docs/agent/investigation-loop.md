# Adaptive Investigation Loop

The investigation loop (`agentic/agent/`) turns the persisted domain model
(`agentic/domain`), the deterministic experiment registry
(`agentic/experiments`), and the input adapters (`agentic/adapters`) into a
genuinely adaptive agent — **not a renamed static pipeline**. Execution paths
differ by goal, intermediate results steer the next experiment, hypotheses move
between states, and the run stops for an explicit reason before concluding.

Entry point: `InvestigationLoop` (`loop.py`) / `run_investigation(...)`. It is wired into
the backend run path behind an off-by-default flag — see
[backend-execution-wiring.md](backend-execution-wiring.md).

## Ten explicit components

| # | Component | Role |
|---|---|---|
| 1 | `GoalInterpreter` | goal text → typed `GoalInterpretation` (intent, metric/group hints, direction). |
| 2 | `HypothesisGenerator` | intent → hypotheses + open questions. |
| 3 | `InvestigationPlanner` | builds **validated** candidate experiments from intent × dataset capabilities (+ falsification candidates from open critiques). |
| 4 | `ExperimentSelector` | policy chooses the next experiment among candidates. |
| 5 | `ExperimentExecutor` | runs the deterministic registry tool, records the result idempotently into state. |
| 6 | `EvidenceUpdater` | converts a result into `Evidence` + `Observation`s, with direction **relative to the hypothesis**. |
| 7 | `HypothesisUpdater` | supports / weakens / rejects / leaves active from the evidence tally; adds follow-up questions. |
| 8 | `Critic` | challenges the strongest supported claim, proposing a falsification experiment. |
| 9 | `TerminationPolicy` | decides continue/stop with a typed `TerminationReason`. |
| 10 | `ConclusionSynthesizer` | after termination, an evidence-linked `Conclusion`. |

## Loop structure

```
interpret goal (model call)
inspect dataset capabilities (manifest roles)
generate initial hypotheses + open questions (model call)
set status running; checkpoint
while not terminated:
    termination pre-check (safety → repeated-failure → budget → sufficient)   [stop?]
    planner: candidate experiments (intent tools ∩ capabilities, + falsifications)
    selector: pick next experiment (model call)          [none → finalize]
    executor: run deterministic tool → ExperimentExecutionRecord
    evidence updater: result → evidence + observations
    hypothesis updater: support / weaken / reject / unresolved
    (weak evidence → follow-up question; next candidate tool becomes the follow-up)
    critic: challenge strongest claim → maybe a falsification experiment (model call)
    advance iteration; checkpoint
synthesize conclusion (only after termination); record TerminationDecision; checkpoint
```

## Why it is adaptive (not a static pipeline)

- **Paths differ by goal.** Intent (trend/comparison/correlation/anomaly/…) maps
  to a different ordered candidate tool set (`INTENT_TOOLS`, plus `EDGAR_*` for
  EDGAR panels). A trend goal runs trend experiments; a comparison goal runs
  comparison experiments (`test_trend_goal_selects_trend_experiments`,
  `test_comparison_goal_selects_comparison_experiments`,
  `test_execution_paths_differ_across_goals`).
- **Intermediate results steer selection.** Candidates exclude already-run tools;
  a weak result keeps the hypothesis unresolved so the loop runs a follow-up
  (`test_weak_result_triggers_followup`); a supported claim makes the critic
  enqueue a falsification experiment that is then selected
  (`test_critic_selects_falsification_experiment`).
- **Hypotheses genuinely change.** Support/weaken/reject/unresolved all occur;
  contradictory evidence (per-entity opposing signals) weakens a hypothesis while
  **preserving both** supporting and contradicting evidence
  (`test_contradictory_evidence_weakens_hypothesis`).
- **Insufficient evidence is a valid conclusion.** Flat data → no directional
  signal → hypotheses left `unresolved` and disposition
  `insufficient_evidence` (`test_insufficient_data_unresolved_conclusion`).

## Bounded parallel experiments

`LoopBudget.max_parallel_experiments` (default **1**) lets one iteration run several
selected experiments concurrently. At the default the loop is strictly sequential and takes
the original code path — no thread pool, no shared-sink wrapper — so existing runs are
unchanged.

**Selection.** The *lead* experiment is chosen by the policy exactly as before: one selector
model call per iteration. Remaining slots are filled deterministically from the planner's
ranked candidates. That keeps `AgentPolicy` a four-method contract, keeps model calls at one
per iteration (so a wider batch *lowers* cost per experiment), and keeps the batch
reproducible. The trade-off — followers are chosen without seeing the lead's result — is
exactly why the batch is bounded.

**The ordering guarantee.** Results are folded into state strictly in *selection* order, never
completion order, so result ids, evidence, and hypothesis updates stay a pure function of
state regardless of how the batch interleaved. `test_results_fold_in_selection_order_not_completion_order`
delays experiments so the batch finishes reversed and asserts state order is unaffected;
`test_resume_matches_an_uninterrupted_batched_run` confirms resume determinism still holds.

Batch width is clamped by whatever budget remains, so a batch never overshoots
`max_experiments` or a caller's `max_new_experiments` window. Deterministic tools are
read-only over the frame; the shared artifact sink is serialized behind `LockedArtifactSink`,
so only emission is synchronized while analysis runs concurrently. A tool that *raises* (an
internal error, as opposed to reporting `status=failed`) propagates identically batched or
not — the pool never swallows it.

## Determinism, persistence, resume

- **Deterministic ids** (`DeterministicIds`, seeded per investigation) make ids a
  pure function of state, so a resumed run mints the same subsequent ids.
- **Every decision is persisted.** Each component appends an `AgentDecision`;
  every iteration checkpoints through an `InvestigationStore`. The in-memory store
  is used in tests; `backend.services.investigation_store.SqlAlchemyInvestigationStore`
  bridges to the durable persistence layer
  (`test_loop_persists_decisions_and_resumes_from_db`).
- **Resume** loads the latest checkpoint and continues; a checkpointed partial run
  resumes to the **same subsequent state** as an uninterrupted run
  (`test_resume_from_checkpoint_matches_uninterrupted`). Resource counters are
  rebuilt from persisted state.

## Failure handling

- **Failed experiments** are recorded (`failed_experiments`), counted toward
  consecutive-failure safety, and do not update evidence.
- **Malformed model output** fails safely: policy validation raises, the loop
  terminates with reason `error`, still synthesizes an (insufficient) conclusion,
  and sets status `failed` (`test_malformed_model_response_fails_safely`).

## Observability

The loop emits a typed event at every decision boundary through an injected
`AgentObserver` (`agentic/agent/observer.py`). The default is a **no-op**, so
observation is off unless an observer is supplied and `agentic/` keeps the
zero-infrastructure-dependency purity required by `domain-boundaries.md` — nothing
in the package imports structlog, OpenTelemetry, or prometheus_client.

| Event | Emitted when |
|---|---|
| `InvestigationStarted` / `InvestigationEnded` | once per `start`/`resume` call; the end event also covers partial (resumable) and failed exits, and carries elapsed time, cost, and model-call count |
| `IterationStarted` / `IterationEnded` | per loop iteration, with duration |
| `ComponentCompleted` | every one of the ten components, with duration and the exception type when it raised |
| `ExperimentObserved` | per executed experiment, with tool, status, duration, evidence produced |
| `HypothesisTransitioned` | whenever a hypothesis actually changes status |
| `ModelCallObserved` | per model-backed component call, with attributed cost |
| `TerminationObserved` | on the typed termination decision |

Components stay observation-free: the loop diffs hypothesis statuses and the budget
tracker around each call, so all instrumentation lives in `loop.py`. `LoopComponent`
is an enum rather than a free string to keep downstream metric label cardinality bounded.

`RecordingObserver` collects events in order for tests and local inspection.

## Time and cost accounting

`InvestigationLoop` takes an injected `Clock` (`agentic/agent/clock.py`) so elapsed-time
behavior is deterministic under test (`ManualClock`). Elapsed time is refreshed at the
top of each iteration, **before** the termination pre-check, so `LoopBudget.max_elapsed_seconds`
and `SafetyLimits.absolute_max_elapsed_seconds` are evaluated against real wall time.

Cost is attributed through the optional `CostAwarePolicy` surface: a policy that knows its
token usage exposes `drain_cost_usd()`, and `_invoke_policy` charges it to the run after each
call, whether or not the call raised. `AgentPolicy` stays a four-method contract — policies
without a cost surface contribute zero and are unaffected.

> Before this wiring, `BudgetTracker.elapsed_seconds` was never assigned and no cost was ever
> accrued, so `max_elapsed_seconds`, `absolute_max_elapsed_seconds` and `max_cost_usd` could
> never fire. `tests/agentic/test_investigation_observability.py` covers each of them.

## The LLM/deterministic split

The `AgentPolicy` (see [`decision-policy.md`](./decision-policy.md)) makes only
*interpretation/selection/critique* decisions, each a typed model call.
**All numbers come from the deterministic experiment registry** — no tool result
is produced or altered by a model.
