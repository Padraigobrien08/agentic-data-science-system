"""
Declining a question the data cannot answer, for the right reason.

A recorded demo asked "which region has the strongest customer loyalty?" of a dataset holding
delivery days, order volume, on-time rate and staff count. Nothing there measures loyalty. The
run proposed a claim about "the loyalty metric", ranked regions by *average delivery days*, and
stopped at ``insufficient_evidence`` — which read, in the product, as a principled decline.

It was not one. The loop had substituted the nearest available metric and then hedged because
that proxy's signal happened to be weak. Had `avg_delivery_days` separated the regions cleanly,
the same code would have reported a confident, well-evidenced answer to a question nobody asked.
Right outcome, wrong reason, and the wrongness was invisible because the outcome vocabulary had
no way to tell "inconclusive" from "unanswerable".

These tests pin the difference: the decline must happen *before* an experiment runs, and it
must be named.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.adapters.base import AdapterRequest
from agentic.adapters.memory import InMemoryDatasetAdapter
from agentic.agent import FixtureAgentPolicy, InMemoryInvestigationStore, InvestigationLoop
from agentic.agent.policy import AnalysisIntent, GoalInterpretation
from agentic.domain.enums import (
    ColumnRole,
    ConclusionDisposition,
    HypothesisStatus,
    TerminationReason,
)

GOAL = "Which region has the strongest customer loyalty?"


def _frame() -> pd.DataFrame:
    months = [f"2024-{m:02d}" for m in range(1, 9)]
    return pd.DataFrame(
        {
            "region": ["north"] * 8 + ["south"] * 8,
            "month": months * 2,
            # Deliberately a clean, strong signal. A decline that only happens because the
            # proxy was noisy is luck; this fixture makes substitution *look* successful, so
            # only a real premise check can produce the right answer.
            "avg_delivery_days": [2.0 + 0.5 * i for i in range(8)] + [9.0 - 0.5 * i for i in range(8)],
            "order_volume": list(range(100, 900, 100)) * 2,
        }
    )


def _manifest(df: pd.DataFrame):
    return InMemoryDatasetAdapter(
        frame=df,
        time_field="month",
        entity_id_fields=["region"],
        role_hints={"avg_delivery_days": ColumnRole.metric, "order_volume": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


class _DeclinesPolicy(FixtureAgentPolicy):
    """A policy that recognises the premise is unsupported — the judgement a model makes."""

    def interpret_goal(self, goal_text: str, *, capability_summary: dict) -> GoalInterpretation:
        return GoalInterpretation(
            intent=AnalysisIntent.ranking,
            answerable=False,
            unsupported_concept="customer loyalty",
            rationale="no column measures loyalty",
        )


class _SubstitutesPolicy(FixtureAgentPolicy):
    """The old behaviour: answer anyway, using whatever metric is nearest."""


@pytest.fixture
def declined():
    frame = _frame()
    return InvestigationLoop(policy=_DeclinesPolicy()).start(
        GOAL, manifest=_manifest(frame), frame=frame, seed="unanswerable",
        store=InMemoryInvestigationStore(),
    )


def test_the_run_stops_for_the_named_reason(declined) -> None:
    assert declined.state.termination is not None
    assert declined.state.termination.reason is TerminationReason.unanswerable_premise


def test_nothing_is_measured_before_declining(declined) -> None:
    """
    The load-bearing assertion. Substituting a metric and *then* hedging produces the same
    termination reason from the outside; what separates a principled decline is that no
    experiment ever ran against the wrong column.
    """
    assert declined.state.completed_experiments == []
    assert declined.state.evidence == []


def test_no_claim_is_made_about_something_the_data_does_not_hold(declined) -> None:
    assert declined.state.hypotheses == []


def test_the_conclusion_says_what_is_missing(declined) -> None:
    conclusion = declined.state.current_conclusion
    assert conclusion is not None
    assert conclusion.disposition is ConclusionDisposition.unanswerable
    assert "customer loyalty" in conclusion.statement
    # No confidence to report: nothing was measured, so a number here would be theatre.
    assert conclusion.confidence == 0.0


def test_the_trace_records_why_it_declined(declined) -> None:
    """A decline the reader cannot explain is indistinguishable from a crash."""
    assert any("customer loyalty" in d.rationale for d in declined.state.decisions)
    assert any("customer loyalty" in q.question for q in declined.state.open_questions)


def test_an_answerable_goal_is_unaffected() -> None:
    """The check must not become a way to decline ordinary work."""
    frame = _frame()
    investigation = InvestigationLoop(policy=_SubstitutesPolicy()).start(
        "Is average delivery time rising over these months?",
        manifest=_manifest(frame), frame=frame, seed="answerable",
        store=InMemoryInvestigationStore(),
    )

    assert investigation.state.termination is not None
    assert investigation.state.termination.reason is not TerminationReason.unanswerable_premise
    assert investigation.state.completed_experiments


def test_a_claim_naming_a_column_that_does_not_exist_loses_the_reference() -> None:
    """
    The backstop for when the policy answers ``answerable=true`` but invents a column. An
    unchecked metric reference does not fail loudly — it falls through to the planner's
    default, which is the same substitution arriving one step later.
    """
    from agentic.agent.budget import BudgetTracker, LoopBudget, SafetyLimits
    from agentic.agent.components import HypothesisGenerator
    from agentic.agent.ids import DeterministicIds
    from agentic.agent.policy import HypothesisProposal, HypothesisProposals
    from agentic.domain import InvestigationGoal, InvestigationState

    class _Invents(FixtureAgentPolicy):
        def generate_hypotheses(self, interpretation, *, metric_names, dimension_names, goal_text=""):
            return HypothesisProposals(
                hypotheses=[
                    HypothesisProposal(statement="loyalty differs by region", metric="loyalty_score"),
                    HypothesisProposal(statement="delivery time is rising", metric="avg_delivery_days"),
                ]
            )

    state = InvestigationState(objective=InvestigationGoal(objective=GOAL))
    HypothesisGenerator(_Invents()).generate(
        GoalInterpretation(intent=AnalysisIntent.ranking),
        state, _manifest(_frame()), DeterministicIds("inv"),
        BudgetTracker(LoopBudget(), SafetyLimits()),
    )

    invented, real = state.hypotheses
    assert invented.metric_refs == [], "a column the dataset does not have must not be referenced"
    assert real.metric_refs == ["avg_delivery_days"], "a real column must survive untouched"
    # The claim itself is kept: a claim nothing can test is a fact about the run worth seeing.
    assert invented.status is HypothesisStatus.proposed
