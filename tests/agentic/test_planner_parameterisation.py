"""
An experiment measures the claim it was created to test.

`InvestigationPlanner` used to parameterise every tool from one global
`interpretation.metric_hint`, and `_target_hypothesis` returned the first matching open
hypothesis rather than serving each in turn. Together those made a second claim
uninvestigable: it was never given candidates, and even if it had been, the experiments would
have measured the first claim's column.

The dedup key is `(tool, metric)` rather than the tool alone. Running one tool against two
different metrics answers two different questions; running it twice against the same metric is
the redundancy the old flat `executed_tools` set existed to prevent.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent.budget import BudgetTracker, LoopBudget, SafetyLimits
from agentic.agent.components import InvestigationPlanner, _prov
from agentic.agent.ids import DeterministicIds
from agentic.agent.policy import AnalysisIntent, GoalInterpretation
from agentic.domain import Hypothesis, InvestigationGoal, InvestigationState
from agentic.domain.enums import ColumnRole
from agentic.experiments import build_default_registry


def _frame(n: int = 10) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entity": ["acme"] * n,
            "quarter": [f"2024-{i:02d}" for i in range(n)],
            "revenue_growth_pct": [20.0 - 1.5 * i for i in range(n)],
            "margin_pct": [31.0 + (i % 2) * 0.2 for i in range(n)],
        }
    )


def _manifest(frame: pd.DataFrame):
    return InMemoryDatasetAdapter(
        frame=frame,
        time_field="quarter",
        entity_id_fields=["entity"],
        role_hints={"revenue_growth_pct": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


def _state(*metrics: str) -> InvestigationState:
    state = InvestigationState(objective=InvestigationGoal(objective="g", adapter_id="generic"))
    for i, metric in enumerate(metrics):
        state.add_hypothesis(
            Hypothesis(
                id=f"h{i}",
                statement=f"{metric} is decreasing over time",
                metric_refs=[metric],
                provenance=_prov("test"),
            )
        )
    return state


def _plan(state, interpretation, manifest):
    planner = InvestigationPlanner(build_default_registry())
    tracker = BudgetTracker(budget=LoopBudget(), safety=SafetyLimits())
    return planner.candidates(state, interpretation, manifest, set(), tracker, DeterministicIds("t"))


def _metric_of(request) -> str | None:
    return request.parameters.get("value_column") or request.parameters.get("column")


_TREND = GoalInterpretation(
    intent=AnalysisIntent.trend, metric_hint="revenue_growth_pct", direction="down"
)


# -- parameterisation --------------------------------------------------------


def test_the_hypothesis_metric_wins_over_the_interpretation_hint() -> None:
    """The claim knows its own column; the interpretation's hint is one value for the whole run."""
    frame = _frame()
    plan = _plan(_state("margin_pct"), _TREND, _manifest(frame))

    assert plan, "no candidates produced"
    assert all(_metric_of(r) == "margin_pct" for r in plan), (
        f"expected every experiment on margin_pct, got {[_metric_of(r) for r in plan]}"
    )


def test_a_hypothesis_without_a_metric_falls_back_to_the_hint() -> None:
    frame = _frame()
    state = InvestigationState(objective=InvestigationGoal(objective="g", adapter_id="generic"))
    state.add_hypothesis(Hypothesis(id="h0", statement="something", provenance=_prov("test")))

    plan = _plan(state, _TREND, _manifest(frame))

    assert all(_metric_of(r) == "revenue_growth_pct" for r in plan)


def test_with_no_hint_at_all_it_falls_back_to_the_first_metric() -> None:
    frame = _frame()
    manifest = _manifest(frame)
    state = InvestigationState(objective=InvestigationGoal(objective="g", adapter_id="generic"))
    state.add_hypothesis(Hypothesis(id="h0", statement="something", provenance=_prov("test")))

    plan = _plan(state, GoalInterpretation(intent=AnalysisIntent.trend), manifest)

    assert all(_metric_of(r) == manifest.metric_names()[0] for r in plan)


def test_two_metric_tools_still_receive_two_columns() -> None:
    """`fit_simple_regression` is inherently multi-metric and must not be squeezed into one."""
    frame = _frame()
    manifest = _manifest(frame)
    plan = _plan(
        _state("revenue_growth_pct"),
        GoalInterpretation(intent=AnalysisIntent.correlation, metric_hint="revenue_growth_pct"),
        manifest,
    )

    regressions = [r for r in plan if r.tool_name == "fit_simple_regression"]
    assert regressions, "correlation intent produced no regression candidate"
    params = regressions[0].parameters
    assert params.get("x_column") and params.get("y_column")
    assert params["x_column"] != params["y_column"]


# -- candidates across claims ------------------------------------------------


def test_every_open_hypothesis_receives_candidates() -> None:
    """The change this phase exists for: a second claim is reachable at all."""
    frame = _frame()
    plan = _plan(_state("revenue_growth_pct", "margin_pct"), _TREND, _manifest(frame))

    metrics = {_metric_of(r) for r in plan}
    targets = {tuple(r.target_hypothesis_ids) for r in plan}

    assert {"revenue_growth_pct", "margin_pct"} <= metrics, f"only reached {metrics}"
    assert ("h0",) in targets and ("h1",) in targets


def test_the_same_tool_can_serve_two_different_claims() -> None:
    """Deduping on the tool alone starved the second claim of every tool the first had used."""
    frame = _frame()
    plan = _plan(_state("revenue_growth_pct", "margin_pct"), _TREND, _manifest(frame))

    trend = [r for r in plan if r.tool_name == "analyze_time_series_trend"]

    assert len(trend) == 2
    assert {_metric_of(r) for r in trend} == {"revenue_growth_pct", "margin_pct"}


def test_a_tool_is_not_offered_twice_for_the_same_metric() -> None:
    """Two claims over one column are genuinely redundant and must collapse to one experiment."""
    frame = _frame()
    plan = _plan(_state("margin_pct", "margin_pct"), _TREND, _manifest(frame))

    pairs = [(r.tool_name, _metric_of(r)) for r in plan]

    assert len(pairs) == len(set(pairs)), f"duplicate (tool, metric) offered: {pairs}"


def test_candidate_ordering_is_stable_across_calls() -> None:
    """Ordering must be a pure function of state — never set or dict iteration order — or ids,
    batching, replay and diff all drift."""
    frame = _frame()
    manifest = _manifest(frame)
    state = _state("revenue_growth_pct", "margin_pct")

    first = [(r.tool_name, _metric_of(r)) for r in _plan(state, _TREND, manifest)]
    second = [(r.tool_name, _metric_of(r)) for r in _plan(state, _TREND, manifest)]

    assert first == second


def test_a_single_hypothesis_plans_exactly_as_before() -> None:
    """
    The equivalence that lets the published scoreboard stand. Ordering for one claim is tool
    priority, unchanged — `tests/agentic/test_core_tier_equivalence.py` pins the end-to-end
    consequence over all 13 frozen cases.
    """
    frame = _frame()
    plan = _plan(_state("revenue_growth_pct"), _TREND, _manifest(frame))

    assert [r.tool_name for r in plan] == [
        "analyze_time_series_trend",
        "detect_change_points",
        "summarize_distribution",
    ]


@pytest.mark.parametrize("metric", ["revenue_growth_pct", "margin_pct"])
def test_executed_pairs_suppress_only_their_own_metric(metric: str) -> None:
    """
    A completed experiment retires its own (tool, metric) pair and nothing else. Before
    `executed_requests` existed this could not be expressed: results record a tool name only.
    """
    frame = _frame()
    manifest = _manifest(frame)
    state = _state("revenue_growth_pct", "margin_pct")

    plan = _plan(state, _TREND, manifest)
    chosen = next(r for r in plan if r.tool_name == "analyze_time_series_trend" and _metric_of(r) == metric)
    state.add_experiment_request(chosen)
    from agentic.domain import ExperimentResult
    from agentic.domain.enums import ExperimentStatus

    state.record_experiment_result(
        ExperimentResult(
            request_id=chosen.id, tool_name=chosen.tool_name,
            status=ExperimentStatus.succeeded, provenance=_prov("test"),
        )
    )

    replanned = [(r.tool_name, _metric_of(r)) for r in _plan(state, _TREND, manifest)]

    assert ("analyze_time_series_trend", metric) not in replanned
    other = "margin_pct" if metric == "revenue_growth_pct" else "revenue_growth_pct"
    assert ("analyze_time_series_trend", other) in replanned
