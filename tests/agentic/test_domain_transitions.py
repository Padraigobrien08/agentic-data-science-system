"""State-transition tests for hypotheses, investigations, and state linking."""

from __future__ import annotations

import pytest

from agentic.domain import (
    BudgetState,
    Evidence,
    EvidenceDirection,
    EvidenceType,
    ExperimentRequest,
    ExperimentResult,
    ExperimentStatus,
    Hypothesis,
    HypothesisStatus,
    IllegalHypothesisTransition,
    IllegalInvestigationTransition,
    Investigation,
    InvestigationGoal,
    InvestigationStatus,
    Observation,
    Provenance,
    ProvenanceSource,
    ReferenceKind,
    SourceReference,
)


def _prov() -> Provenance:
    return Provenance(source=ProvenanceSource.agent_llm, agent_id="a")


def _hyp(**kw) -> Hypothesis:
    return Hypothesis(statement="h", provenance=_prov(), **kw)


def test_legal_hypothesis_path() -> None:
    h = _hyp()
    assert h.status is HypothesisStatus.proposed
    h.set_status(HypothesisStatus.active)
    h.set_status(HypothesisStatus.supported)
    h.set_status(HypothesisStatus.weakened)  # supported -> weakened allowed
    assert h.status is HypothesisStatus.weakened


def test_illegal_hypothesis_transition_raises() -> None:
    h = _hyp()
    # proposed -> supported is not allowed (must go active first)
    with pytest.raises(IllegalHypothesisTransition):
        h.set_status(HypothesisStatus.supported)
    # rejected is terminal
    h.set_status(HypothesisStatus.active)
    h.set_status(HypothesisStatus.rejected)
    assert h.is_terminal()
    with pytest.raises(IllegalHypothesisTransition):
        h.set_status(HypothesisStatus.active)


def test_hypothesis_touch_updates_timestamp() -> None:
    h = _hyp()
    before = h.updated_at
    h.set_status(HypothesisStatus.active)
    assert h.updated_at >= before
    # no-op transition to same status does not error
    h.set_status(HypothesisStatus.active)


def test_investigation_status_transitions() -> None:
    inv = Investigation.start(InvestigationGoal(objective="g"))
    assert inv.status is InvestigationStatus.created
    inv.set_status(InvestigationStatus.planning)
    inv.set_status(InvestigationStatus.running)
    inv.set_status(InvestigationStatus.converged)
    assert inv.is_terminal()
    with pytest.raises(IllegalInvestigationTransition):
        inv.set_status(InvestigationStatus.running)


def test_investigation_cannot_skip_to_running() -> None:
    inv = Investigation.start(InvestigationGoal(objective="g"))
    with pytest.raises(IllegalInvestigationTransition):
        inv.set_status(InvestigationStatus.running)  # created -> running is illegal


def test_add_evidence_links_by_direction() -> None:
    inv = Investigation.start(InvestigationGoal(objective="g"))
    state = inv.state
    h = state.add_hypothesis(_hyp())

    support = state.add_evidence(
        Evidence(
            evidence_type=EvidenceType.anomaly_flag,
            source_reference=SourceReference(kind=ReferenceKind.artifact, ref="a"),
            hypothesis_ids=[h.id],
            claim="supports",
            direction=EvidenceDirection.supports,
            provenance=_prov(),
        )
    )
    refute = state.add_evidence(
        Evidence(
            evidence_type=EvidenceType.peer_comparison,
            source_reference=SourceReference(kind=ReferenceKind.artifact, ref="b"),
            hypothesis_ids=[h.id],
            claim="refutes",
            direction=EvidenceDirection.refutes,
            provenance=_prov(),
        )
    )
    assert support.id in h.supporting_evidence_ids
    assert refute.id in h.contradicting_evidence_ids
    assert state.evidence_for(h.id) == [support, refute]


def test_record_experiment_result_files_and_counts() -> None:
    inv = Investigation.start(InvestigationGoal(objective="g"))
    state = inv.state
    req = state.add_experiment_request(
        ExperimentRequest(tool_name="t", purpose="p", provenance=_prov())
    )
    assert state.pending_experiments == [req]

    ok = ExperimentResult(
        request_id=req.id,
        tool_name="t",
        status=ExperimentStatus.succeeded,
        observations=[Observation(statement="o", provenance=_prov())],
        provenance=_prov(),
    )
    state.record_experiment_result(ok)
    assert state.pending_experiments == []           # pending cleared
    assert state.completed_experiments == [ok]
    assert state.budget.experiments_used == 1
    assert len(state.observations) == 1              # observations lifted into state

    bad = ExperimentResult(
        request_id="other",
        tool_name="t",
        status=ExperimentStatus.failed,
        provenance=_prov(),
    )
    state.record_experiment_result(bad)
    assert state.failed_experiments == [bad]
    assert state.budget.experiments_used == 2


def test_budget_exhaustion() -> None:
    b = BudgetState(max_experiments=2)
    assert not b.is_exhausted()
    b.experiments_used = 2
    assert b.is_exhausted()


def test_open_question_resolution() -> None:
    from agentic.domain import OpenQuestion, OpenQuestionStatus

    q = OpenQuestion(question="q?", provenance=_prov())
    assert q.status is OpenQuestionStatus.open
    q.resolve("answer", evidence_ids=["evd_1"])
    assert q.status is OpenQuestionStatus.answered
    assert q.answer == "answer"
    assert "evd_1" in q.answered_by_evidence_ids
