"""
A goal that asks "which of these two?" must not be answered "both".

A published demo asked whether NVDA's margin advantage reflected durable profitability *or*
was explained by faster revenue growth, and concluded **both, at 0.95 each**, with
``contradiction_found: false``. The product rendered it as "2 claims stood up to the evidence"
— the most confident card in the showcase, on the run where the reasoning failed.

Nothing was broken in the sense of throwing. Each claim was scored honestly against its own
evidence, which is exactly how a claim and its negation can both reach ``supported``: the
hypothesis updater never compares claims to each other. The only component that saw them
together was the critic, and the critic asks a *model* whether two statements are mutually
exclusive. That check is real, and it is best-effort by construction. It missed.

The fix does not make the model better at noticing. It removes the need to notice: the goal's
own phrasing establishes the rivalry before any claim is scored, so the conflict is provable
rather than observable.

The second half of this file is about the dead end that made the guarantee unusable even when
it fired. ``Critique.resolved`` was never set to ``True`` anywhere in the codebase, so any run
that recorded a contradiction could never again reach ``sufficient_evidence`` — not even after
the discriminating experiment settled it.
"""

from __future__ import annotations

from agentic.agent.components import (
    enforce_mutual_exclusivity,
    open_contradictions,
    reconcile_contradictions,
)
from agentic.agent.ids import DeterministicIds
from agentic.domain import Hypothesis, InvestigationGoal, InvestigationState
from agentic.domain.enums import CritiqueType, HypothesisStatus, ProvenanceSource
from agentic.domain.provenance import Provenance

_PROV = Provenance(source=ProvenanceSource.agent_llm, agent_id="test")

EITHER_OR = (
    "Does NVDA's margin advantage reflect a durable difference in profitability, "
    "or is it explained by faster revenue growth over the same periods?"
)


def _rivals(*, goal: str = EITHER_OR, statuses=(HypothesisStatus.supported,) * 2):
    """Two claims the goal poses as alternatives, at whatever statuses a test needs."""
    state = InvestigationState(objective=InvestigationGoal(objective=goal))
    for i, (statement, status) in enumerate(
        zip(["durable profitability", "faster revenue growth"], statuses)
    ):
        claim = Hypothesis(id=f"hyp-{i}", statement=statement, provenance=_PROV)
        claim.set_confidence(0.95)
        claim.set_status(HypothesisStatus.active)
        claim.set_status(status)
        state.add_hypothesis(claim)
    first, second = state.hypotheses
    first.mutually_exclusive_with = [second.id]
    second.mutually_exclusive_with = [first.id]
    return state


def _idgen() -> DeterministicIds:
    return DeterministicIds("inv")


# -- the conflict is proved, not noticed -------------------------------------


def test_both_branches_standing_records_a_contradiction() -> None:
    state = _rivals()

    recorded = enforce_mutual_exclusivity(state, _idgen())

    assert len(recorded) == 1
    assert recorded[0].critique_type is CritiqueType.contradiction


def test_neither_side_is_left_standing() -> None:
    """The conflict says one of them is wrong, not which — so neither is picked."""
    state = _rivals()

    enforce_mutual_exclusivity(state, _idgen())

    assert [h.status for h in state.hypotheses] == [
        HypothesisStatus.weakened,
        HypothesisStatus.weakened,
    ]
    assert all(h.confidence <= 0.5 for h in state.hypotheses)


def test_the_contradiction_names_both_sides() -> None:
    """Storing only the critiqued claim is what made the conflict impossible to resolve."""
    state = _rivals()

    critique = enforce_mutual_exclusivity(state, _idgen())[0]

    assert {critique.target.id, critique.conflicts_with_id} == {"hyp-0", "hyp-1"}


def test_the_trace_explains_the_weakening() -> None:
    state = _rivals()

    enforce_mutual_exclusivity(state, _idgen())

    rationales = [d.rationale for d in state.decisions]
    assert any("cannot hold at the same time as" in r for r in rationales)
    assert state.open_questions


def test_it_does_not_fire_twice_on_the_same_pair() -> None:
    state = _rivals()
    idgen = _idgen()

    enforce_mutual_exclusivity(state, idgen)
    # Restore both to supported, as fresh evidence legitimately could.
    for claim in state.hypotheses:
        claim.set_status(HypothesisStatus.supported)

    assert enforce_mutual_exclusivity(state, idgen) != [], (
        "a pair restored to supported by new evidence is a live conflict again"
    )
    assert len([c for c in state.critiques if c.critique_type is CritiqueType.contradiction]) == 2


def test_only_one_side_standing_is_not_a_conflict() -> None:
    """This is the run answering the question, which is the outcome we want."""
    state = _rivals(statuses=(HypothesisStatus.supported, HypothesisStatus.rejected))

    assert enforce_mutual_exclusivity(state, _idgen()) == []


def test_a_goal_that_asks_about_two_things_independently_is_untouched() -> None:
    """Marking unrelated claims as rivals would suppress a legitimate 'both are true'."""
    state = _rivals(goal="Compare revenue or margin by region.")
    for claim in state.hypotheses:
        claim.mutually_exclusive_with = []

    assert enforce_mutual_exclusivity(state, _idgen()) == []


# -- the dead end ------------------------------------------------------------


def test_an_open_conflict_is_reported_while_both_are_weakened() -> None:
    state = _rivals()
    enforce_mutual_exclusivity(state, _idgen())

    assert open_contradictions(state), "a conflict nothing has separated is still open"


def test_evidence_separating_the_pair_settles_the_conflict() -> None:
    """
    The path that did not exist. ``resolved`` defaulted to False and was never assigned, so
    ``sufficient_evidence`` was unreachable for the rest of any run that recorded a conflict.
    """
    state = _rivals()
    enforce_mutual_exclusivity(state, _idgen())

    # The discriminating experiment lands: one explanation survives, the other does not.
    state.hypotheses[0].set_status(HypothesisStatus.supported)
    state.hypotheses[1].set_status(HypothesisStatus.rejected)
    reconcile_contradictions(state)

    assert not open_contradictions(state)
    assert all(
        c.resolved for c in state.critiques if c.critique_type is CritiqueType.contradiction
    )


def test_a_conflict_that_stays_unseparated_is_never_marked_settled() -> None:
    """Both still weakened means the question was put and not answered."""
    state = _rivals()
    enforce_mutual_exclusivity(state, _idgen())

    reconcile_contradictions(state)

    assert open_contradictions(state)


def test_both_sides_supported_again_is_not_settled() -> None:
    state = _rivals()
    enforce_mutual_exclusivity(state, _idgen())
    for claim in state.hypotheses:
        claim.set_status(HypothesisStatus.supported)

    reconcile_contradictions(state)

    assert open_contradictions(state), "two claims both standing is the conflict, not its answer"
