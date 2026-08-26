"""
Which claim the critic challenges, and why it is being asked.

A ``supported`` claim keeps priority — that is the behaviour the agency suite's
``require_challenge`` property measures. Below it sit three shapes the run's evidence can take,
each a different question. The gate stopped at supported-or-mixed until the published corpus
showed what that cost: of five runs that ran any experiment, three never consulted the critic
at all, including the flagship, which ran seven experiments and rejected both its claims
without one.

The reason travels with the claim because it decides what a useful challenge *is*. "You may be
overconfident" and "your measurements are not separating anything" are different questions.
"""

from __future__ import annotations

from agentic.agent.components import Critic
from agentic.agent.policy import ChallengeReason
from agentic.domain import (
    Evidence,
    EvidenceDirection,
    Hypothesis,
    HypothesisStatus,
    InvestigationGoal,
    InvestigationState,
)
from agentic.domain.enums import EvidenceType, ProvenanceSource, ReferenceKind
from agentic.domain.evidence import SourceReference
from agentic.domain.provenance import Provenance

_PROV = Provenance(source=ProvenanceSource.agent_llm, agent_id="test")


def _state(*hypotheses: Hypothesis) -> InvestigationState:
    state = InvestigationState(objective=InvestigationGoal(objective="why did it move?"))
    for h in hypotheses:
        state.add_hypothesis(h)
    return state


def _hyp(hid: str, status: HypothesisStatus, confidence: float = 0.5) -> Hypothesis:
    h = Hypothesis(id=hid, statement=f"{hid} moved", rationale="", provenance=_PROV)
    # Statuses are a transition graph, not free assignment: everything routes through `active`.
    if status is not HypothesisStatus.proposed:
        h.set_status(HypothesisStatus.active)
    if status not in (HypothesisStatus.proposed, HypothesisStatus.active):
        h.set_status(status)
    h.confidence = confidence
    return h


def _evidence(eid: str, hid: str, direction: EvidenceDirection) -> Evidence:
    return Evidence(
        id=eid,
        evidence_type=EvidenceType.descriptive_stat,
        source_reference=SourceReference(kind=ReferenceKind.experiment_result, ref="exp-1"),
        hypothesis_ids=[hid],
        claim=f"{hid} evidence",
        direction=direction,
        provenance=_PROV,
    )


def test_no_hypotheses_means_nothing_to_challenge() -> None:
    assert Critic._claim_to_challenge(_state()) is None


def test_a_supported_claim_is_challenged_first() -> None:
    """Unchanged priority: guarding against false confidence is the critic's primary job."""
    state = _state(
        _hyp("h1", HypothesisStatus.active, 0.9),
        _hyp("h2", HypothesisStatus.supported, 0.7),
    )
    state.add_evidence(_evidence("e1", "h1", EvidenceDirection.supports))
    state.add_evidence(_evidence("e2", "h1", EvidenceDirection.refutes))

    chosen = Critic._claim_to_challenge(state)
    assert chosen is not None
    claim, reason = chosen
    assert claim.id == "h2"
    assert reason is ChallengeReason.false_confidence


def test_a_claim_with_mixed_evidence_is_challenged_when_none_is_supported() -> None:
    state = _state(_hyp("h1", HypothesisStatus.weakened))
    state.add_evidence(_evidence("e1", "h1", EvidenceDirection.supports))
    state.add_evidence(_evidence("e2", "h1", EvidenceDirection.refutes))

    chosen = Critic._claim_to_challenge(state)
    assert chosen is not None
    claim, reason = chosen
    assert claim.id == "h1"
    assert reason is ChallengeReason.conflicting_evidence


def test_a_claim_only_refuted_is_challenged_before_it_is_dropped() -> None:
    """One method disagreeing is a reason to look again, not a verdict.

    This used to assert ``None`` — "one-sided evidence, nothing to weigh". That reading is why
    a run whose claims were being knocked down got no second reading at all.
    """
    state = _state(_hyp("h1", HypothesisStatus.weakened))
    state.add_evidence(_evidence("e1", "h1", EvidenceDirection.refutes))
    state.add_evidence(_evidence("e2", "h1", EvidenceDirection.refutes))

    chosen = Critic._claim_to_challenge(state)
    assert chosen is not None
    claim, reason = chosen
    assert claim.id == "h1"
    assert reason is ChallengeReason.unexplained_refutation


def test_a_claim_measured_only_neutrally_is_challenged() -> None:
    """The run measured and separated nothing. Ask for a method that would.

    The shape of `csv-distribution-honesty`, which ran three experiments, produced three
    neutral records and declined — never once asking whether a different method discriminates.
    """
    state = _state(_hyp("h1", HypothesisStatus.active))
    for i in range(3):
        state.add_evidence(_evidence(f"e{i}", "h1", EvidenceDirection.neutral))

    chosen = Critic._claim_to_challenge(state)
    assert chosen is not None
    claim, reason = chosen
    assert claim.id == "h1"
    assert reason is ChallengeReason.undiscriminating_evidence


def test_supporting_evidence_short_of_supported_is_not_challenged() -> None:
    """The remaining half of the old one-sided rule, and it still holds.

    The first tier catches this the moment the claim reaches ``supported``. Challenging it
    earlier would fire on every iteration of a perfectly healthy run.
    """
    state = _state(_hyp("h1", HypothesisStatus.active))
    state.add_evidence(_evidence("e1", "h1", EvidenceDirection.supports))
    state.add_evidence(_evidence("e2", "h1", EvidenceDirection.supports))

    assert Critic._claim_to_challenge(state) is None


def test_a_claim_with_no_evidence_is_not_challenged() -> None:
    assert Critic._claim_to_challenge(_state(_hyp("h1", HypothesisStatus.active))) is None


def test_rejected_and_unresolved_claims_are_left_alone() -> None:
    """Both are settled; re-challenging them spends budget on a closed question."""
    for status in (HypothesisStatus.rejected, HypothesisStatus.unresolved):
        state = _state(_hyp("h1", status))
        state.add_evidence(_evidence("e1", "h1", EvidenceDirection.supports))
        state.add_evidence(_evidence("e2", "h1", EvidenceDirection.refutes))
        assert Critic._claim_to_challenge(state) is None, status


def test_conflicting_outranks_undiscriminating_and_refuted() -> None:
    """Tier order: the claim whose evidence actually disagrees with itself comes first."""
    state = _state(
        _hyp("neutral_only", HypothesisStatus.active, 0.9),
        _hyp("conflicting", HypothesisStatus.active, 0.4),
    )
    state.add_evidence(_evidence("e1", "neutral_only", EvidenceDirection.neutral))
    state.add_evidence(_evidence("e2", "conflicting", EvidenceDirection.supports))
    state.add_evidence(_evidence("e3", "conflicting", EvidenceDirection.refutes))

    chosen = Critic._claim_to_challenge(state)
    assert chosen is not None
    claim, reason = chosen
    # Chosen despite the *lower* confidence: the tier decides before confidence does.
    assert claim.id == "conflicting"
    assert reason is ChallengeReason.conflicting_evidence
