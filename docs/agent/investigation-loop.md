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

## The LLM/deterministic split

The `AgentPolicy` (see [`decision-policy.md`](./decision-policy.md)) makes only
*interpretation/selection/critique* decisions, each a typed model call.
**All numbers come from the deterministic experiment registry** — no tool result
is produced or altered by a model.
