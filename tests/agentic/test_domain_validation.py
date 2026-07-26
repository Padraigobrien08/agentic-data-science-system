"""Validation tests for the investigation domain entities."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic.domain import (
    ColumnRole,
    ColumnSpec,
    Conclusion,
    ConclusionDisposition,
    DatasetManifest,
    DatasetProvenance,
    Evidence,
    EvidenceDirection,
    EvidenceType,
    Hypothesis,
    HypothesisStatus,
    Provenance,
    ProvenanceSource,
    ReferenceKind,
    SourceReference,
    new_id,
)


def _prov() -> Provenance:
    return Provenance(source=ProvenanceSource.agent_llm, agent_id="planner")


def test_ids_are_prefixed_and_stable() -> None:
    h = Hypothesis(statement="x", provenance=_prov())
    assert h.id.startswith("hyp_")
    # id does not change across model operations / serialization
    dumped = h.model_dump(mode="json")
    assert dumped["id"] == h.id
    assert new_id("abc").startswith("abc_")


def test_confidence_is_bounded() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(statement="x", confidence=1.5, provenance=_prov())
    with pytest.raises(ValidationError):
        Hypothesis(statement="x", confidence=-0.1, provenance=_prov())
    ok = Hypothesis(statement="x", confidence=1.0, provenance=_prov())
    assert ok.confidence == 1.0


def test_evidence_quality_scores_bounded() -> None:
    ref = SourceReference(kind=ReferenceKind.artifact, ref="a.csv")
    for bad in ("strength", "reliability", "coverage"):
        with pytest.raises(ValidationError):
            Evidence(
                evidence_type=EvidenceType.anomaly_flag,
                source_reference=ref,
                claim="c",
                direction=EvidenceDirection.supports,
                provenance=_prov(),
                **{bad: 2.0},
            )


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(statement="x", provenance=_prov(), bogus=1)  # type: ignore[call-arg]


def test_required_fields_enforced() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(provenance=_prov())  # missing statement  # type: ignore[call-arg]
    with pytest.raises(ValidationError):
        Hypothesis(statement="")  # empty statement + missing provenance  # type: ignore[call-arg]


def test_provenance_is_required_first_class() -> None:
    # provenance is a required, typed field — not an optional dict
    with pytest.raises(ValidationError):
        Hypothesis(statement="x")  # type: ignore[call-arg]
    h = Hypothesis(statement="x", provenance=_prov())
    assert h.provenance.source is ProvenanceSource.agent_llm
    assert isinstance(h.provenance, Provenance)


def test_enum_values_validated() -> None:
    with pytest.raises(ValidationError):
        Hypothesis(statement="x", status="not_a_status", provenance=_prov())  # type: ignore[arg-type]
    h = Hypothesis(statement="x", status=HypothesisStatus.active, provenance=_prov())
    assert h.status is HypothesisStatus.active


def test_conclusion_confidence_bounded_and_disposition_enum() -> None:
    with pytest.raises(ValidationError):
        Conclusion(
            statement="s",
            disposition=ConclusionDisposition.supported,
            confidence=9.0,
            provenance=_prov(),
        )
    c = Conclusion(statement="s", disposition=ConclusionDisposition.inconclusive, provenance=_prov())
    assert c.disposition is ConclusionDisposition.inconclusive


def test_manifest_has_schema_version_and_roles() -> None:
    m = DatasetManifest(
        name="panel",
        columns=[ColumnSpec(name="net_margin", role=ColumnRole.metric)],
        provenance=DatasetProvenance(adapter_id="edgar", source="test"),
    )
    assert m.schema_version
    assert m.metric_names() == ["net_margin"]
