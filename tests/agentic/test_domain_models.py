"""Unit tests for the input-agnostic investigation domain entities."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic.domain import (
    ColumnRole,
    ColumnSpec,
    DatasetKind,
    DatasetManifest,
    DatasetProvenance,
    Evidence,
    EvidenceDirection,
    EvidenceRef,
    Experiment,
    ExperimentResult,
    ExperimentStatus,
    Hypothesis,
    HypothesisStatus,
    InvestigationGoal,
    InvestigationState,
    InvestigationStatus,
    TerminationDecision,
    TerminationReason,
)


def _manifest() -> DatasetManifest:
    return DatasetManifest(
        name="panel",
        columns=[
            ColumnSpec(name="ticker", dtype="str", role=ColumnRole.entity_id, nullable=False),
            ColumnSpec(name="period", dtype="period", role=ColumnRole.time_index),
            ColumnSpec(name="revenue", dtype="float", role=ColumnRole.metric, unit="USD"),
            ColumnSpec(name="net_margin", dtype="float", role=ColumnRole.metric, unit="ratio"),
        ],
        entities=["AAPL", "MSFT"],
        provenance=DatasetProvenance(adapter_id="edgar", source="test"),
    )


def test_manifest_role_accessors() -> None:
    m = _manifest()
    assert m.metric_names() == ["revenue", "net_margin"]
    assert m.entity_id_column().name == "ticker"
    assert m.time_index_column().name == "period"
    assert [c.name for c in m.columns_with_role(ColumnRole.metric)] == ["revenue", "net_margin"]


def test_manifest_is_json_serializable_and_roundtrips() -> None:
    m = _manifest()
    dumped = m.model_dump(mode="json")
    assert dumped["dataset_kind"] == DatasetKind.tabular_panel.value
    restored = DatasetManifest.model_validate(dumped)
    assert restored.metric_names() == m.metric_names()
    assert restored.manifest_id == m.manifest_id


def test_manifest_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        DatasetManifest(
            name="x",
            provenance=DatasetProvenance(adapter_id="edgar", source="test"),
            bogus_field=1,  # type: ignore[call-arg]
        )


def test_hypothesis_confidence_bounds_enforced() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(statement="x", confidence=1.5)
    h = Hypothesis(statement="revenue spike is anomalous")
    assert h.status is HypothesisStatus.proposed
    assert 0.0 <= h.confidence <= 1.0


def test_experiment_typed_inputs_and_terminal() -> None:
    exp = Experiment(tool_name="detect_anomalies", inputs={"metric": "revenue", "threshold": 2.5})
    assert exp.status is ExperimentStatus.planned
    assert not exp.is_terminal()
    exp.result = ExperimentResult(status=ExperimentStatus.succeeded, metrics={"anomaly_count": 3.0})
    exp.status = ExperimentStatus.succeeded
    assert exp.is_terminal()
    # round-trip preserves typed outputs
    restored = Experiment.model_validate(exp.model_dump(mode="json"))
    assert restored.result.metrics["anomaly_count"] == 3.0


def test_investigation_add_evidence_links_hypothesis() -> None:
    state = InvestigationState(
        goal=InvestigationGoal(text="find unusual changes", adapter_id="edgar"),
    )
    state.bind_manifest(_manifest())
    assert state.status is InvestigationStatus.created

    hyp = state.add_hypothesis(Hypothesis(statement="net_margin deteriorated"))
    ev = state.add_evidence(
        Evidence(
            hypothesis_ids=[hyp.hypothesis_id],
            claim="net_margin fell 3 quarters running",
            direction=EvidenceDirection.supports,
            strength=0.8,
            refs=[EvidenceRef(kind="artifact", ref="anomalies.csv", locator="row=12")],
        )
    )
    # evidence back-links onto the hypothesis
    assert ev.evidence_id in state.find_hypothesis(hyp.hypothesis_id).evidence_ids
    assert state.evidence_for(hyp.hypothesis_id) == [ev]


def test_investigation_iteration_and_termination_state() -> None:
    state = InvestigationState(goal=InvestigationGoal(text="g", adapter_id="edgar"))
    assert state.advance_iteration() == 1
    state.set_status(InvestigationStatus.running)

    decision = TerminationDecision(
        should_stop=True,
        reason=TerminationReason.sufficient_evidence,
        rationale="two supporting experiments converged",
        at_iteration=state.iteration,
    )
    state.record_termination(decision)
    assert state.termination.should_stop is True
    assert state.termination.reason is TerminationReason.sufficient_evidence

    # whole aggregate survives a JSON round-trip (reproducible from persisted state)
    restored = InvestigationState.model_validate(state.model_dump(mode="json"))
    assert restored.iteration == 1
    assert restored.termination.reason is TerminationReason.sufficient_evidence


def test_open_hypotheses_and_pending_experiments() -> None:
    state = InvestigationState(goal=InvestigationGoal(text="g", adapter_id="edgar"))
    h_open = state.add_hypothesis(Hypothesis(statement="a"))
    h_done = state.add_hypothesis(Hypothesis(statement="b", status=HypothesisStatus.supported))
    state.add_experiment(Experiment(tool_name="t1"))
    state.add_experiment(Experiment(tool_name="t2", status=ExperimentStatus.succeeded))

    assert state.open_hypotheses() == [h_open]
    assert h_done not in state.open_hypotheses()
    assert [e.tool_name for e in state.pending_experiments()] == ["t1"]
