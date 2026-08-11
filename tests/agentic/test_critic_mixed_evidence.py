"""
Which claim the critic challenges.

A ``supported`` claim keeps priority — that is the behaviour the agency suite's
``require_challenge`` property measures. The addition is that a claim with *mixed* evidence is
also challenged, because restricting the critic to supported claims meant no run ending
inconclusive was ever challenged, and those are the runs a second reading helps most.
"""

from __future__ import annotations

from agentic.agent.components import Critic
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
    assert chosen is not None and chosen.id == "h2"


def test_a_claim_with_mixed_evidence_is_challenged_when_none_is_supported() -> None:
    state = _state(_hyp("h1", HypothesisStatus.weakened))
    state.add_evidence(_evidence("e1", "h1", EvidenceDirection.supports))
    state.add_evidence(_evidence("e2", "h1", EvidenceDirection.refutes))

    chosen = Critic._claim_to_challenge(state)
    assert chosen is not None and chosen.id == "h1"


def test_one_sided_evidence_is_not_challenged() -> None:
    """Nothing to weigh — a critique here would be a note, not a challenge."""
    state = _state(_hyp("h1", HypothesisStatus.weakened))
    state.add_evidence(_evidence("e1", "h1", EvidenceDirection.refutes))
    state.add_evidence(_evidence("e2", "h1", EvidenceDirection.refutes))

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
