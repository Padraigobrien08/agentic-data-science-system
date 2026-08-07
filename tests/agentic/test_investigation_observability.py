"""
Observability seam + budget enforcement for the adaptive investigation loop.

Two things are proven here:

1. **The loop is observable.** Every decision boundary emits a typed event —
   run start/end, iterations, all ten components (including ones that raise),
   experiments, hypothesis transitions, model calls with cost, and termination.
   Observation is off by default and never changes loop behavior.
2. **The elapsed-time and cost limits actually fire.** Before this seam,
   ``BudgetTracker.elapsed_seconds`` was never assigned and no cost was ever
   attributed, so ``max_elapsed_seconds``, ``absolute_max_elapsed_seconds`` and
   ``max_cost_usd`` were unreachable. These tests fail without the wiring.

All offline and deterministic (``ManualClock``).
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent import (
    ComponentCompleted,
    ExperimentObserved,
    FixtureAgentPolicy,
    HypothesisTransitioned,
    InMemoryInvestigationStore,
    InvestigationEnded,
    InvestigationLoop,
    InvestigationStarted,
    IterationEnded,
    IterationStarted,
    LoopBudget,
    LoopComponent,
    ManualClock,
    ModelAgentPolicy,
    ModelCallObserved,
    RecordingObserver,
    SafetyLimits,
    TerminationObserved,
)
from agentic.domain.enums import ColumnRole, TerminationReason


def _manifest(df: pd.DataFrame, **hints):
    return InMemoryDatasetAdapter(frame=df, **hints).build_manifest(AdapterRequest())


def _trending_up(entity: str = "A", n: int = 8, start: float = 10.0, step: float = 5.0) -> pd.DataFrame:
    periods = [f"2021-Q{i % 4 + 1}-{i // 4}" for i in range(n)]
    return pd.DataFrame({"entity": [entity] * n, "period": periods,
                         "revenue": [start + step * i for i in range(n)]})


def _trend_case():
    df = _trending_up()
    m = _manifest(df, time_field="period", entity_id_fields=["entity"],
                  role_hints={"revenue": ColumnRole.metric})
    return df, m


class _TickingClock(ManualClock):
    """Advances a fixed amount on every reading, so elapsed time grows on its own."""

    def __init__(self, step: float) -> None:
        super().__init__()
        self._step = step

    def monotonic(self) -> float:
        self.now += self._step
        return self.now


class _CostlyPolicy(FixtureAgentPolicy):
    """Deterministic policy that reports a fixed cost per model call."""

    def __init__(self, cost_per_call: float) -> None:
        super().__init__()
        self._cost_per_call = cost_per_call
        self._pending = 0.0
        self.calls = 0

    def _charge(self) -> None:
        self.calls += 1
        self._pending += self._cost_per_call

    def drain_cost_usd(self) -> float:
        pending, self._pending = self._pending, 0.0
        return pending

    def interpret_goal(self, *a, **kw):
        self._charge()
        return super().interpret_goal(*a, **kw)

    def generate_hypotheses(self, *a, **kw):
        self._charge()
        return super().generate_hypotheses(*a, **kw)

    def select_experiment(self, *a, **kw):
        self._charge()
        return super().select_experiment(*a, **kw)

    def critique(self, *a, **kw):
        self._charge()
        return super().critique(*a, **kw)


# -- 1. observation is off by default and behavior-neutral -------------------


def test_default_loop_runs_without_an_observer() -> None:
    df, m = _trend_case()
    inv = InvestigationLoop().start("what is the revenue trend over time?", manifest=m, frame=df,
                                    seed="noobs", store=InMemoryInvestigationStore())
    assert inv.is_terminal()


def test_observer_does_not_change_the_outcome() -> None:
    df, m = _trend_case()
    plain = InvestigationLoop().start("what is the revenue trend over time?", manifest=m, frame=df,
                                      seed="same", store=InMemoryInvestigationStore())
    observed = InvestigationLoop(observer=RecordingObserver()).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="same",
        store=InMemoryInvestigationStore())
    assert plain.status is observed.status
    assert plain.state.termination.reason is observed.state.termination.reason
    assert ([r.tool_name for r in plain.state.completed_experiments]
            == [r.tool_name for r in observed.state.completed_experiments])


# -- 2. the full lifecycle is emitted ---------------------------------------


def test_lifecycle_events_cover_the_whole_run() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    inv = InvestigationLoop(observer=obs).start("what is the revenue trend over time?", manifest=m,
                                                frame=df, seed="life", store=InMemoryInvestigationStore())

    started = obs.of_type(InvestigationStarted)
    ended = obs.of_type(InvestigationEnded)
    assert len(started) == 1 and len(ended) == 1
    assert started[0].investigation_id == inv.id
    assert started[0].resumed is False
    assert started[0].dataset_name == m.name

    end = ended[0]
    assert end.partial is False
    assert end.status is inv.status
    assert end.termination_reason is inv.state.termination.reason
    assert end.iterations == inv.state.budget.iterations_used
    assert end.experiments_completed == len(inv.state.completed_experiments)
    assert end.hypotheses == len(inv.state.hypotheses)
    assert end.model_calls > 0

    terminated = obs.of_type(TerminationObserved)
    assert len(terminated) == 1
    assert terminated[0].reason is inv.state.termination.reason

    # iterations are paired and numbered consistently
    starts = obs.of_type(IterationStarted)
    ends = obs.of_type(IterationEnded)
    assert len(starts) >= 1
    assert [e.iteration for e in ends] == [s.iteration for s in starts[:len(ends)]]

    # the run's last event is always the end event
    assert isinstance(obs.events[-1], InvestigationEnded)


def test_component_events_cover_the_ten_components() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    InvestigationLoop(observer=obs).start("what is the revenue trend over time?", manifest=m, frame=df,
                                          seed="components", store=InMemoryInvestigationStore())
    seen = {e.component for e in obs.of_type(ComponentCompleted)}
    assert {
        LoopComponent.goal_interpreter,
        LoopComponent.hypothesis_generator,
        LoopComponent.planner,
        LoopComponent.selector,
        LoopComponent.executor,
        LoopComponent.evidence_updater,
        LoopComponent.hypothesis_updater,
        LoopComponent.critic,
        LoopComponent.termination_policy,
        LoopComponent.conclusion_synthesizer,
    } <= seen
    assert all(e.duration_seconds >= 0 for e in obs.of_type(ComponentCompleted))
    assert all(e.error is None for e in obs.of_type(ComponentCompleted))


def test_experiment_events_match_executed_experiments() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    inv = InvestigationLoop(observer=obs).start("what is the revenue trend over time?", manifest=m,
                                                frame=df, seed="exp", store=InMemoryInvestigationStore())
    events = obs.of_type(ExperimentObserved)
    executed = [r.tool_name for r in inv.state.completed_experiments + inv.state.failed_experiments]
    assert [e.tool_name for e in events] == executed
    assert any(e.evidence_produced > 0 for e in events)


def test_hypothesis_transitions_are_emitted() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    InvestigationLoop(observer=obs).start("revenue is increasing over time", manifest=m, frame=df,
                                          seed="trans", store=InMemoryInvestigationStore())
    transitions = obs.of_type(HypothesisTransitioned)
    assert transitions, "a supported hypothesis should produce at least one status transition"
    assert all(t.from_status is not t.to_status for t in transitions)


# -- 3. failures are observable ---------------------------------------------


def test_component_failure_is_reported_with_its_error() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    # A responder returning non-JSON makes the goal interpreter raise MalformedPolicyResponse.
    loop = InvestigationLoop(policy=ModelAgentPolicy(lambda system, user: "not json"), observer=obs)
    inv = loop.start("what is the revenue trend over time?", manifest=m, frame=df, seed="broken",
                     store=InMemoryInvestigationStore())

    failed = [e for e in obs.of_type(ComponentCompleted) if e.error is not None]
    assert failed, "the raising component must still emit a completion event"
    assert failed[0].component is LoopComponent.goal_interpreter
    assert failed[0].error == "MalformedPolicyResponse"
    # the run still terminates safely, and the end event is still emitted
    assert inv.state.termination.reason is TerminationReason.error
    assert obs.of_type(InvestigationEnded)[0].termination_reason is TerminationReason.error


def test_partial_run_is_reported_as_partial() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    inv = InvestigationLoop(observer=obs).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="partial",
        max_new_experiments=1, store=InMemoryInvestigationStore())
    assert not inv.is_terminal()
    ended = obs.of_type(InvestigationEnded)
    assert len(ended) == 1 and ended[0].partial is True
    assert ended[0].termination_reason is None
    assert not obs.of_type(TerminationObserved)


def test_resume_is_reported_as_resumed() -> None:
    df, m = _trend_case()
    store = InMemoryInvestigationStore()
    loop = InvestigationLoop()
    inv = loop.start("what is the revenue trend over time?", manifest=m, frame=df, seed="res",
                     max_new_experiments=1, store=store)
    obs = RecordingObserver()
    InvestigationLoop(observer=obs).resume(inv, goal_text="what is the revenue trend over time?",
                                           manifest=m, frame=df, store=store)
    assert obs.of_type(InvestigationStarted)[0].resumed is True


# -- 4. elapsed-time limits now actually fire -------------------------------


def test_elapsed_budget_terminates_the_run() -> None:
    """Regression: ``max_elapsed_seconds`` was unreachable while elapsed was never set."""
    df, m = _trend_case()
    inv = InvestigationLoop(clock=_TickingClock(step=10.0)).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="elapsed",
        budget=LoopBudget(max_elapsed_seconds=5.0), store=InMemoryInvestigationStore())
    assert inv.is_terminal()
    assert inv.state.termination.reason is TerminationReason.budget_exhausted
    assert not inv.state.completed_experiments, "the budget should stop the run before any experiment"


def test_absolute_elapsed_safety_cap_terminates_the_run() -> None:
    """Regression: the safety cap was unreachable for the same reason."""
    df, m = _trend_case()
    inv = InvestigationLoop(clock=_TickingClock(step=10.0)).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="safety",
        # a generous budget, so only the absolute safety cap can stop this run
        budget=LoopBudget(max_elapsed_seconds=10_000.0),
        safety=SafetyLimits(absolute_max_elapsed_seconds=5.0),
        store=InMemoryInvestigationStore())
    assert inv.is_terminal()
    assert inv.state.termination.reason is TerminationReason.safety_constraint


def test_elapsed_is_reported_on_the_end_event() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    InvestigationLoop(observer=obs, clock=_TickingClock(step=0.5)).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="elapsed-report",
        store=InMemoryInvestigationStore())
    assert obs.of_type(InvestigationEnded)[0].elapsed_seconds > 0


# -- 5. cost is attributed and enforced -------------------------------------


def test_cost_is_attributed_from_a_cost_aware_policy() -> None:
    df, m = _trend_case()
    obs = RecordingObserver()
    policy = _CostlyPolicy(cost_per_call=0.01)
    InvestigationLoop(policy=policy, observer=obs).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="cost",
        store=InMemoryInvestigationStore())

    calls = obs.of_type(ModelCallObserved)
    assert calls, "model-backed components must report their calls"
    assert all(c.cost_usd == pytest.approx(0.01) for c in calls)
    assert {c.component for c in calls} <= {
        LoopComponent.goal_interpreter, LoopComponent.hypothesis_generator,
        LoopComponent.selector, LoopComponent.critic,
    }
    end = obs.of_type(InvestigationEnded)[0]
    assert end.cost_usd == pytest.approx(0.01 * policy.calls)


def test_cost_budget_terminates_the_run() -> None:
    """Regression: ``max_cost_usd`` was unreachable while cost was never accrued."""
    df, m = _trend_case()
    inv = InvestigationLoop(policy=_CostlyPolicy(cost_per_call=1.0)).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="cost-cap",
        budget=LoopBudget(max_cost_usd=1.5), store=InMemoryInvestigationStore())
    assert inv.is_terminal()
    assert inv.state.termination.reason is TerminationReason.budget_exhausted


def test_cost_free_policies_are_unaffected() -> None:
    """A policy with no cost surface must still run to a normal (non-budget) end."""
    df, m = _trend_case()
    obs = RecordingObserver()
    inv = InvestigationLoop(observer=obs).start(
        "what is the revenue trend over time?", manifest=m, frame=df, seed="free",
        budget=LoopBudget(max_cost_usd=0.01), store=InMemoryInvestigationStore())
    assert inv.state.termination.reason is not TerminationReason.budget_exhausted
    assert obs.of_type(InvestigationEnded)[0].cost_usd == 0.0
