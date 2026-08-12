"""
What "done" and "concluded" mean when an investigation holds several claims.

33-01 made a second claim reachable. Without this, the loop still stopped the moment the first
claim was supported, so the second was stranded at `proposed` one step later than before — the
same bug wearing a different hat.

Two decisions are pinned here.

**Sufficiency is about the investigation, not one claim.** The bar is "nothing is still
`proposed`", deliberately not `Hypothesis.is_terminal()`: only `rejected` is terminal in the
transition graph, so requiring terminality would require every claim to be *rejected*. A claim
past `proposed` has had evidence brought to bear on it.

**A split outcome is `mixed`, not `supported`.** Reporting one supported and one refuted claim
as supported drops the refutation from the headline and averages its confidence away — the
overclaiming the agency suite exists to punish, in our own synthesis code.
"""

from __future__ import annotations

import pandas as pd
import pytest

from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.agent.loop import InvestigationLoop
from agentic.agent.policy import (
    AnalysisIntent,
    GoalInterpretation,
    HypothesisProposal,
    HypothesisProposals,
)
from agentic.domain.enums import ColumnRole, ConclusionDisposition, HypothesisStatus

_N = 10


def _frame() -> pd.DataFrame:
    """One metric that clearly falls, one that clearly does not."""
    return pd.DataFrame(
        {
            "entity": ["acme"] * _N,
            "quarter": [f"2024-{i:02d}" for i in range(_N)],
            "revenue_growth_pct": [20.0 - 1.5 * i for i in range(_N)],
            "margin_pct": [31.0 + (i % 2) * 0.2 for i in range(_N)],
        }
    )


def _manifest(frame: pd.DataFrame):
    return InMemoryDatasetAdapter(
        frame=frame,
        time_field="quarter",
        entity_id_fields=["entity"],
        role_hints={"revenue_growth_pct": ColumnRole.metric},
    ).build_manifest(AdapterRequest())


def _policy(*metrics: str):
    class _Claims(FixtureAgentPolicy):
        def interpret_goal(self, goal_text, *, capability_summary):  # noqa: ANN001
            return GoalInterpretation(
                intent=AnalysisIntent.trend, metric_hint=metrics[0], direction="down"
            )

        def generate_hypotheses(self, interpretation, *, metric_names, dimension_names, goal_text=""):  # noqa: ANN001
            return HypothesisProposals(
                hypotheses=[
                    HypothesisProposal(
                        statement=f"{m} is decreasing over time", metric=m, direction="down"
                    )
                    for m in metrics
                ],
                questions=[],
            )

    return _Claims()


def _run(*metrics: str, seed: str = "t", **kwargs):
    frame = _frame()
    return InvestigationLoop(policy=_policy(*metrics)).start(
        "goal", manifest=_manifest(frame), frame=frame, seed=seed, **kwargs
    )


# -- sufficiency across claims -----------------------------------------------


def test_a_second_claim_is_no_longer_stranded() -> None:
    """
    The regression this phase exists for. Verified in 28-02 as
    `[(['revenue_growth_pct'],'supported'), (['margin_pct'],'proposed')]` — the second claim
    never investigated by any policy, however well it reasoned.
    """
    inv = _run("revenue_growth_pct", "margin_pct")

    statuses = {h.metric_refs[0]: h.status for h in inv.state.hypotheses}

    assert statuses["margin_pct"] is not HypothesisStatus.proposed, (
        "the second claim was never investigated"
    )


def test_both_claims_are_measured_on_their_own_metric() -> None:
    inv = _run("revenue_growth_pct", "margin_pct")

    measured = {
        r.parameters.get("value_column") or r.parameters.get("column")
        for r in inv.state.executed_requests
    }

    assert {"revenue_growth_pct", "margin_pct"} <= measured


def test_sufficiency_does_not_fire_while_a_claim_is_untouched() -> None:
    """A run that stopped here would report success with a question unanswered."""
    inv = _run("revenue_growth_pct", "margin_pct")

    proposed = [h for h in inv.state.hypotheses if h.status is HypothesisStatus.proposed]

    assert not proposed, f"terminated with {len(proposed)} claim(s) never investigated"


def test_a_single_claim_run_is_unchanged() -> None:
    """
    One claim resolved *is* every claim resolved, so single-claim behaviour must be identical.
    `tests/agentic/test_core_tier_equivalence.py` pins this over all 13 frozen cases; this is
    the direct statement of the invariant.
    """
    inv = _run("revenue_growth_pct")

    assert inv.state.termination is not None
    assert inv.state.termination.reason.value == "sufficient_evidence"
    assert [h.status for h in inv.state.hypotheses] == [HypothesisStatus.supported]


def test_an_unresolvable_claim_still_reaches_a_typed_terminal_state() -> None:
    """Blocking sufficiency must not be able to hang the loop."""
    inv = _run("revenue_growth_pct", "margin_pct")

    assert inv.state.termination is not None
    assert inv.state.termination.reason is not None


# -- the conclusion ----------------------------------------------------------


def test_a_split_outcome_is_reported_as_mixed() -> None:
    inv = _run("revenue_growth_pct", "margin_pct")
    conclusion = inv.state.current_conclusion

    assert conclusion is not None
    assert conclusion.disposition is ConclusionDisposition.mixed


def test_the_mixed_statement_names_both_sides() -> None:
    """The refutation has to survive into the headline, not just the hypothesis list."""
    inv = _run("revenue_growth_pct", "margin_pct")
    statement = inv.state.current_conclusion.statement

    assert "revenue_growth_pct" in statement
    assert "margin_pct" in statement


def test_mixed_confidence_is_below_the_all_supported_case() -> None:
    mixed = _run("revenue_growth_pct", "margin_pct").state.current_conclusion
    all_supported = _run("revenue_growth_pct", seed="single").state.current_conclusion

    assert mixed.confidence < all_supported.confidence


def test_an_all_supported_run_keeps_its_disposition_and_confidence() -> None:
    """The single-group branches are untouched."""
    conclusion = _run("revenue_growth_pct").state.current_conclusion

    assert conclusion.disposition is ConclusionDisposition.supported
    assert conclusion.confidence == pytest.approx(0.95)


def test_every_claim_appears_in_the_mixed_conclusions_hypothesis_ids() -> None:
    inv = _run("revenue_growth_pct", "margin_pct")
    conclusion = inv.state.current_conclusion

    assert set(conclusion.supporting_hypothesis_ids) == {h.id for h in inv.state.hypotheses}


# -- budget ------------------------------------------------------------------


def test_a_two_claim_run_completes_under_the_default_budget() -> None:
    """
    Experiments scale with claim count. If the default cannot carry two claims, multi-part
    questions silently become `budget_exhausted` rather than answers.
    """
    inv = _run("revenue_growth_pct", "margin_pct")

    assert inv.state.termination.reason.value != "budget_exhausted"


def test_resuming_a_multi_claim_run_reproduces_the_same_state() -> None:
    """Longer runs are likelier to be resumed mid-flight, so this path needs its own coverage."""
    frame = _frame()
    manifest = _manifest(frame)
    policy = _policy("revenue_growth_pct", "margin_pct")

    full = InvestigationLoop(policy=policy).start(
        "goal", manifest=manifest, frame=frame, seed="resume"
    )
    partial = InvestigationLoop(policy=policy).start(
        "goal", manifest=manifest, frame=frame, seed="resume", max_new_experiments=1
    )
    resumed = InvestigationLoop(policy=policy).resume(
        partial, goal_text="goal", manifest=manifest, frame=frame
    )

    assert [r.tool_name for r in resumed.state.executed_requests] == [
        r.tool_name for r in full.state.executed_requests
    ]
    assert [h.status for h in resumed.state.hypotheses] == [h.status for h in full.state.hypotheses]
