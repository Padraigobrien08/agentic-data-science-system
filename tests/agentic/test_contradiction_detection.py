"""
The loop refusing to hold two claims that cannot both be true.

Nothing else compares hypotheses to each other — :class:`HypothesisUpdater` scores each one
against the evidence routed to it — so a claim and its negation can both reach ``supported``.
That is not hypothetical: a real recording produced

    [supported @ 0.95] On-time rate is more strongly associated with staffing than volume.
    [supported @ 0.95] Order volume is a stronger driver of service quality than staffing.

and still terminated ``sufficient_evidence``. The critic is the only component that sees the
supported set together, so detection lives there; what a detection *does* is computed here,
never by the model.
"""

from __future__ import annotations

import pytest

from agentic.agent.budget import BudgetTracker, LoopBudget, SafetyLimits
from agentic.agent.components import Critic, TerminationPolicy
from agentic.agent.ids import DeterministicIds
from agentic.agent.policy import AnalysisIntent, CritiqueProposal, GoalInterpretation
from agentic.domain import (
    ColumnRole,
    ColumnSpec,
    DatasetManifest,
    DatasetProvenance,
    Hypothesis,
    InvestigationGoal,
    InvestigationState,
)
from agentic.domain.enums import (
    CritiqueType,
    HypothesisStatus,
    ProvenanceSource,
    TerminationReason,
)
from agentic.domain.provenance import Provenance

_PROV = Provenance(source=ProvenanceSource.agent_llm, agent_id="test")

#: A plain tabular manifest — not EDGAR, so the critic offers the general tool set.
_MANIFEST = DatasetManifest(
    name="delivery",
    columns=[ColumnSpec(name="on_time_rate", role=ColumnRole.metric)],
    provenance=DatasetProvenance(adapter_id="in_memory", source="test"),
)


def _supported(hid: str, statement: str, confidence: float) -> Hypothesis:
    h = Hypothesis(id=hid, statement=statement, rationale="", provenance=_PROV)
    # Statuses are a transition graph, not free assignment: everything routes through `active`.
    h.set_status(HypothesisStatus.active)
    h.set_status(HypothesisStatus.supported)
    h.set_confidence(confidence)
    return h


class _Policy:
    """Critic policy returning a scripted proposal, recording what it was shown."""

    def __init__(self, proposal: CritiqueProposal) -> None:
        self._proposal = proposal
        self.seen_supported: list[dict] | None = None

    def critique(self, *, strongest_claim, available_tools, supported_claims=None):  # noqa: ANN001, ANN201
        self.seen_supported = supported_claims
        return self._proposal

    def interpret_goal(self, *a, **k):  # pragma: no cover - unused
        raise NotImplementedError

    def generate_hypotheses(self, *a, **k):  # pragma: no cover - unused
        raise NotImplementedError

    def select_experiment(self, *a, **k):  # pragma: no cover - unused
        raise NotImplementedError


def _tracker() -> BudgetTracker:
    """The real tracker — a stub would only pin the surface the critic happens to call today."""
    return BudgetTracker(budget=LoopBudget(), safety=SafetyLimits())


@pytest.fixture
def state() -> InvestigationState:
    st = InvestigationState(objective=InvestigationGoal(objective="does staffing or volume drive service?"))
    st.add_hypothesis(_supported(
        "h-a", "Staffing is the stronger driver of on-time rate than volume.", 0.95))
    st.add_hypothesis(_supported(
        "h-b", "Volume is a stronger driver of on-time rate than staffing.", 0.95))
    return st


def _run_critic(state: InvestigationState, proposal: CritiqueProposal) -> _Policy:
    policy = _Policy(proposal)
    Critic(policy).challenge(
        state,
        GoalInterpretation(intent=AnalysisIntent.correlation),
        manifest=_MANIFEST,
        executed_tools=set(),
        tracker=_tracker(),
        idgen=DeterministicIds("seed"),
    )
    return policy


CONTRADICTION = CritiqueProposal(
    should_challenge=True,
    target_hypothesis_id="h-a",
    contradicts_hypothesis_id="h-b",
    falsification_tool="fit_simple_regression",
    message="These cannot both hold.",
    rationale="mutually exclusive orderings",
)


def test_a_decline_that_still_names_a_conflict_is_acted_on(state) -> None:
    """
    The shape a real run actually produces.

    By the time both claims are supported the strongest has usually been critiqued and the
    tool list is empty, so the policy declines the ordinary challenge — `should_challenge:
    false`, null target — and reports the conflict alongside it. Requiring a target here
    silently dropped the one report this feature exists to catch, and every unit test that
    set both ids missed it.
    """
    _run_critic(state, CritiqueProposal(
        should_challenge=False,
        target_hypothesis_id=None,
        contradicts_hypothesis_id="h-b",
        message="The two supported claims are mutually exclusive.",
        rationale="already critiqued and no tools left, but the conflict stands",
    ))

    assert state.find_hypothesis("h-a").status is HypothesisStatus.weakened
    assert state.find_hypothesis("h-b").status is HypothesisStatus.weakened
    assert [c for c in state.critiques if c.critique_type is CritiqueType.contradiction]


def test_the_policy_is_shown_every_supported_claim(state) -> None:
    """Detection is impossible unless the critic can see the claims side by side."""
    policy = _run_critic(state, CritiqueProposal(should_challenge=False))

    assert {c["id"] for c in policy.seen_supported} == {"h-a", "h-b"}
    assert all("statement" in c for c in policy.seen_supported)


def test_both_sides_are_weakened_not_one_chosen(state) -> None:
    """The conflict establishes that they cannot both hold, not which one is wrong."""
    _run_critic(state, CONTRADICTION)

    a = state.find_hypothesis("h-a")
    b = state.find_hypothesis("h-b")
    assert a.status is HypothesisStatus.weakened
    assert b.status is HypothesisStatus.weakened
    assert a.confidence <= Critic.CONTRADICTION_CONFIDENCE_CAP
    assert b.confidence <= Critic.CONTRADICTION_CONFIDENCE_CAP


def test_a_contradiction_critique_and_open_question_are_recorded(state) -> None:
    _run_critic(state, CONTRADICTION)

    crit = [c for c in state.critiques if c.critique_type is CritiqueType.contradiction]
    assert len(crit) == 1
    assert crit[0].resolved is False
    # The pair linkage lives on the open question, which carries a list of hypothesis ids.
    assert {"h-a", "h-b"} == set(state.open_questions[0].related_hypothesis_ids)


def test_both_claims_get_a_recorded_decision(state) -> None:
    """A status change with no decision behind it is a number with no provenance."""
    _run_critic(state, CONTRADICTION)

    targeted = {d.targets[0].id for d in state.decisions if "contradicts" in d.rationale}
    assert targeted == {"h-a", "h-b"}


def test_a_contradiction_blocks_sufficient_evidence(state) -> None:
    _run_critic(state, CONTRADICTION)

    stop, reason = TerminationPolicy().decide(
        state, _tracker(), iterations=3,
        executed_tools={"fit_simple_regression"}, intent_tools=[], user_stop=False,
    )

    assert stop is True
    assert reason is TerminationReason.insufficient_evidence


def test_the_discriminating_experiment_runs_before_concluding(state) -> None:
    """When the critic names a tool that could settle it, the loop tries that first."""
    _run_critic(state, CONTRADICTION)

    stop, reason = TerminationPolicy().decide(
        state, _tracker(), iterations=3,
        executed_tools=set(),  # the suggested tool has not run
        intent_tools=[], user_stop=False,
    )

    assert stop is False
    assert reason is None


def test_running_out_of_experiments_does_not_settle_a_contradiction(state) -> None:
    _run_critic(state, CONTRADICTION)

    assert TerminationPolicy().finalize_no_candidates(state, ran_any=True) is (
        TerminationReason.insufficient_evidence
    )


def test_a_third_standing_claim_does_not_rescue_sufficiency(state) -> None:
    """Sufficiency is about the investigation, so one clean claim cannot mask the conflict."""
    state.add_hypothesis(_supported("h-c", "Unrelated and well supported.", 0.9))
    _run_critic(state, CONTRADICTION)

    assert TerminationPolicy().finalize_no_candidates(state, ran_any=True) is (
        TerminationReason.insufficient_evidence
    )


def test_running_out_of_experiments_with_an_untested_claim_is_not_sufficiency(state) -> None:
    """
    The two termination paths must apply the same bar.

    ``decide`` already refuses to conclude while a claim sits at `proposed`, but
    ``finalize_no_candidates`` did not — so a run that exhausted its candidates could report
    `sufficient_evidence` with a rival explanation untested. One did: it concluded "a genuine
    change rather than a seasonal artifact" at 0.95 while the seasonality claim it raised had
    nothing run against it.
    """
    st = InvestigationState(objective=InvestigationGoal(objective="break or seasonality?"))
    st.add_hypothesis(_supported("h-1", "The break is a genuine change.", 0.95))
    st.add_hypothesis(Hypothesis(
        id="h-2", statement="Seasonality explains the break.", rationale="", provenance=_PROV))

    assert st.find_hypothesis("h-2").status is HypothesisStatus.proposed
    assert TerminationPolicy().finalize_no_candidates(st, ran_any=True) is (
        TerminationReason.insufficient_evidence
    )


def test_all_claims_tested_still_reaches_sufficiency(state) -> None:
    """The guard must not make sufficiency unreachable."""
    st = InvestigationState(objective=InvestigationGoal(objective="did it move?"))
    st.add_hypothesis(_supported("h-1", "It moved.", 0.95))

    assert TerminationPolicy().finalize_no_candidates(st, ran_any=True) is (
        TerminationReason.sufficient_evidence
    )


# ------------------------------------------------------------------ what must NOT fire


def test_no_contradiction_reported_leaves_the_claims_alone(state) -> None:
    _run_critic(state, CritiqueProposal(
        should_challenge=True, target_hypothesis_id="h-a",
        falsification_tool="fit_simple_regression", message="ordinary challenge",
    ))

    assert state.find_hypothesis("h-a").status is HypothesisStatus.supported
    assert not [c for c in state.critiques if c.critique_type is CritiqueType.contradiction]


def test_a_claim_contradicting_itself_is_ignored(state) -> None:
    """Guards against the model echoing the target id back into the new field."""
    _run_critic(state, CritiqueProposal(
        should_challenge=True, target_hypothesis_id="h-a", contradicts_hypothesis_id="h-a",
        falsification_tool="fit_simple_regression", message="self",
    ))

    assert state.find_hypothesis("h-a").status is HypothesisStatus.supported
    assert not [c for c in state.critiques if c.critique_type is CritiqueType.contradiction]


def test_an_unknown_hypothesis_id_is_ignored(state) -> None:
    _run_critic(state, CritiqueProposal(
        should_challenge=True, target_hypothesis_id="h-a", contradicts_hypothesis_id="h-nope",
        falsification_tool="fit_simple_regression", message="hallucinated id",
    ))

    assert state.find_hypothesis("h-a").status is HypothesisStatus.supported
    assert not [c for c in state.critiques if c.critique_type is CritiqueType.contradiction]


def test_a_claim_that_is_no_longer_supported_cannot_be_contradicted(state) -> None:
    """A weakened claim is not being asserted, so there is nothing to conflict with."""
    # `weakened` rather than `rejected`: the transition graph allows only that from
    # `supported`, which is also why the contradiction handler weakens rather than rejects.
    state.find_hypothesis("h-b").set_status(HypothesisStatus.weakened)

    _run_critic(state, CONTRADICTION)

    assert state.find_hypothesis("h-a").status is HypothesisStatus.supported
    assert not [c for c in state.critiques if c.critique_type is CritiqueType.contradiction]


def test_recording_is_idempotent_for_the_same_pair(state) -> None:
    """Weakening the pair is what stops a second call re-firing on it."""
    _run_critic(state, CONTRADICTION)
    _run_critic(state, CONTRADICTION)

    assert len([c for c in state.critiques if c.critique_type is CritiqueType.contradiction]) == 1
