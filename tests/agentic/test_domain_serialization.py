"""Serialization round-trip tests: every entity survives model_dump(mode='json')."""

from __future__ import annotations

import json

from agentic.domain import (
    AgentDecision,
    Conclusion,
    ConclusionDisposition,
    Critique,
    CritiqueType,
    DecisionType,
    EntityKind,
    EntityRef,
    Evidence,
    EvidenceDirection,
    EvidenceType,
    ExperimentRequest,
    ExperimentResult,
    ExperimentStatus,
    Hypothesis,
    Investigation,
    InvestigationState,
    Observation,
    OpenQuestion,
    Provenance,
    ProvenanceSource,
    ReferenceKind,
    ReproducibilityManifest,
    SourceReference,
)
from agentic.domain.examples import example_inconclusive_investigation, example_investigation


def _prov() -> Provenance:
    return Provenance(source=ProvenanceSource.agent_llm, agent_id="a")


def test_investigation_roundtrip_preserves_state() -> None:
    inv = example_investigation()
    dumped = inv.model_dump(mode="json")
    # dumped must be pure JSON (no non-serializable objects)
    text = json.dumps(dumped)
    restored = Investigation.model_validate(json.loads(text))
    assert restored.id == inv.id
    assert restored.status == inv.status
    assert len(restored.state.hypotheses) == len(inv.state.hypotheses)
    assert len(restored.state.evidence) == len(inv.state.evidence)
    assert restored.state.termination.reason == inv.state.termination.reason
    assert restored.state.current_conclusion.disposition == inv.state.current_conclusion.disposition
    # nested links survive
    hyp = restored.state.hypotheses[0]
    assert restored.state.evidence[0].id in hyp.supporting_evidence_ids


def test_inconclusive_investigation_roundtrip() -> None:
    inv = example_inconclusive_investigation()
    restored = Investigation.model_validate(json.loads(inv.model_dump_json()))
    assert restored.state.termination.reason.value == "insufficient_evidence"
    assert restored.state.budget.max_experiments == 2


def test_each_entity_roundtrips_individually() -> None:
    entities = [
        Hypothesis(statement="h", provenance=_prov()),
        Evidence(
            evidence_type=EvidenceType.statistical_test,
            source_reference=SourceReference(kind=ReferenceKind.artifact, ref="a"),
            claim="c",
            direction=EvidenceDirection.supports,
            provenance=_prov(),
        ),
        Observation(statement="o", provenance=_prov()),
        ExperimentRequest(tool_name="t", purpose="p", provenance=_prov()),
        ExperimentResult(request_id="r", tool_name="t", status=ExperimentStatus.succeeded, provenance=_prov()),
        OpenQuestion(question="q?", provenance=_prov()),
        AgentDecision(decision_type=DecisionType.select_experiment, rationale="r", provenance=_prov()),
        Critique(
            critique_type=CritiqueType.overreach,
            target=EntityRef(kind=EntityKind.hypothesis, id="hyp_1"),
            message="m",
            provenance=_prov(),
        ),
        Conclusion(statement="s", disposition=ConclusionDisposition.supported, provenance=_prov()),
        ReproducibilityManifest(random_seed=7, tool_versions={"detect_anomalies": "1"}),
    ]
    for e in entities:
        cls = type(e)
        restored = cls.model_validate(json.loads(e.model_dump_json()))
        assert restored.model_dump(mode="json") == e.model_dump(mode="json")


def test_empty_state_roundtrips() -> None:
    from agentic.domain import InvestigationGoal

    state = InvestigationState(objective=InvestigationGoal(objective="g"))
    restored = InvestigationState.model_validate(json.loads(state.model_dump_json()))
    assert restored.objective.objective == "g"
    assert restored.version
