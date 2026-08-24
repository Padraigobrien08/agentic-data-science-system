"""
Two competing explanations about the same metric must both get tested.

The recording stack tells you to phrase every goal as two rival accounts — "is it staffing,
or is it volume?" — and rivals about one outcome are, almost by definition, two claims about
one metric. The planner deduped candidates by ``(tool, metric)`` with the seen-set shared
across claims, so the first claim took every key and the second was given nothing: it sat at
``proposed`` until the tool list ran out, and the loop then refused to conclude because an
untested alternative was still standing. Correct behaviour, impossible situation.

Observed in a real recording: both claims carried ``metric_refs=["revenue_growth_qoq"]``,
four experiments ran, and every one of them named ``hyp-0``.
"""

from __future__ import annotations

import pytest

from agentic.agent.budget import BudgetTracker, LoopBudget, SafetyLimits
from agentic.agent.components import InvestigationPlanner
from agentic.agent.ids import DeterministicIds
from agentic.agent.policy import AnalysisIntent, GoalInterpretation
from agentic.domain import (
    ColumnRole,
    ColumnSpec,
    DatasetManifest,
    DatasetProvenance,
    Hypothesis,
    InvestigationGoal,
    InvestigationState,
)
from agentic.domain.enums import ProvenanceSource
from agentic.domain.provenance import Provenance
from agentic.experiments import build_default_registry

_PROV = Provenance(source=ProvenanceSource.agent_llm, agent_id="test")

_MANIFEST = DatasetManifest(
    name="ops",
    columns=[
        ColumnSpec(name="period", role=ColumnRole.time_index),
        ColumnSpec(name="region", role=ColumnRole.dimension),
        ColumnSpec(name="on_time_rate", role=ColumnRole.metric),
        ColumnSpec(name="order_volume", role=ColumnRole.metric),
    ],
    provenance=DatasetProvenance(adapter_id="in_memory", source="test"),
)


def _state(*metrics: str) -> InvestigationState:
    state = InvestigationState(objective=InvestigationGoal(objective="staffing or volume?"))
    for i, metric in enumerate(metrics):
        state.add_hypothesis(
            Hypothesis(
                id=f"hyp-{i}",
                statement=f"claim {i} about {metric}",
                metric_refs=[metric],
                provenance=_PROV,
            )
        )
    return state


def _candidates(state: InvestigationState):
    tracker = BudgetTracker(LoopBudget(), SafetyLimits())
    return InvestigationPlanner(build_default_registry()).candidates(
        state,
        GoalInterpretation(intent=AnalysisIntent.trend, metric_hint="on_time_rate"),
        _MANIFEST,
        executed_tools=set(),
        tracker=tracker,
        idgen=DeterministicIds("inv"),
    )


def test_both_claims_about_one_metric_are_named_by_the_experiments() -> None:
    requests = _candidates(_state("on_time_rate", "on_time_rate"))

    assert requests, "the planner produced no candidates at all"
    named = {h for r in requests for h in r.target_hypothesis_ids}
    assert named == {"hyp-0", "hyp-1"}


def test_the_shared_experiment_is_raised_once_not_twice() -> None:
    # The same tool over the same metric returns the same numbers. Running it per claim
    # would spend twice and double-count the evidence it produced.
    requests = _candidates(_state("on_time_rate", "on_time_rate"))

    tools = [r.tool_name for r in requests]
    assert len(tools) == len(set(tools))
    assert all(len(r.target_hypothesis_ids) == 2 for r in requests)


def test_claims_on_different_metrics_still_get_their_own_experiments() -> None:
    # The grouping must not collapse claims that genuinely measure different things.
    state = _state("on_time_rate")
    state.add_hypothesis(
        Hypothesis(id="hyp-1", statement="a claim about volume", metric_refs=["order_volume"],
                   provenance=_PROV)
    )

    requests = _candidates(state)

    by_claim: dict[str, set[str]] = {}
    for r in requests:
        for h in r.target_hypothesis_ids:
            by_claim.setdefault(h, set()).add(r.tool_name)
    assert set(by_claim) == {"hyp-0", "hyp-1"}
    # Each claim's experiments are its own, not a shared set naming both.
    assert all(len(r.target_hypothesis_ids) == 1 for r in requests)


def test_a_single_claim_is_unchanged() -> None:
    requests = _candidates(_state("on_time_rate"))

    assert requests
    assert all(r.target_hypothesis_ids == ["hyp-0"] for r in requests)


@pytest.mark.parametrize("run", range(3))
def test_candidate_order_is_deterministic(run: int) -> None:
    """Ids, batching, replay and diff all depend on this being a pure function of state."""
    first = [(r.id, r.tool_name, tuple(r.target_hypothesis_ids)) for r in _candidates(_state("on_time_rate", "on_time_rate"))]
    second = [(r.id, r.tool_name, tuple(r.target_hypothesis_ids)) for r in _candidates(_state("on_time_rate", "on_time_rate"))]

    assert first == second
