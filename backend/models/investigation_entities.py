"""
Investigation reasoning entities — normalized, FK-integrous projection.

Hypotheses, evidence, experiment requests/results, observations, decisions,
critiques, open questions, and conclusions. Evidence and experiment results link
to the existing ``artifacts`` table (artifact linkage). Experiment results carry
an idempotency key with a per-investigation unique constraint so retries never
create duplicate results.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.artifact import Artifact
    from backend.models.investigation import Investigation


def _fk_inv() -> Mapped[uuid.UUID]:
    return mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )


class HypothesisRow(Base):
    __tablename__ = "hypotheses"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    prior_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    parent_hypothesis_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hypotheses.id", ondelete="SET NULL"), nullable=True
    )
    metric_refs_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    entity_refs_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="hypotheses")


class ExperimentRequestRow(Base):
    __tablename__ = "experiment_requests"
    __table_args__ = (UniqueConstraint("investigation_id", "domain_id", name="uq_experiment_request_domain_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    definition_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    parameters_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_hypothesis_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    cost_estimate_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    expected_information_gain: Mapped[float | None] = mapped_column(Float, nullable=True)
    preconditions_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reproducibility_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reproducibility_manifests.id", ondelete="SET NULL"), nullable=True
    )
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="experiment_requests")


class ExperimentResultRow(Base):
    __tablename__ = "experiment_results"
    __table_args__ = (
        UniqueConstraint("investigation_id", "idempotency_key", name="uq_experiment_result_idempotency"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    request_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("experiment_requests.id", ondelete="SET NULL"), nullable=True, index=True
    )
    request_domain_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    tool_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(
        String(128), nullable=False, index=True,
        doc="Retries with the same computation reuse the existing row (default: output/input fingerprint).",
    )
    input_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    output_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    metrics_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    statistics_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    reproducibility_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reproducibility_manifests.id", ondelete="SET NULL"), nullable=True
    )
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="experiment_results")
    artifact_links: Mapped[list[ExperimentResultArtifactLink]] = relationship(
        "ExperimentResultArtifactLink", back_populates="experiment_result", cascade="all, delete-orphan"
    )


class ObservationRow(Base):
    __tablename__ = "observations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    experiment_result_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("experiment_results.id", ondelete="SET NULL"), nullable=True, index=True
    )
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    observation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    magnitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    entity_ref: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    metric_ref: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    data_reference_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="observations")


class EvidenceRow(Base):
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    evidence_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    claim: Mapped[str] = mapped_column(Text, nullable=False)
    direction: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    strength: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    reliability: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    experiment_result_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("experiment_results.id", ondelete="SET NULL"), nullable=True, index=True
    )
    source_reference_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    payload_reference_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    statistics_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="evidence")
    hypothesis_links: Mapped[list[EvidenceHypothesisLink]] = relationship(
        "EvidenceHypothesisLink", back_populates="evidence", cascade="all, delete-orphan"
    )
    artifact_links: Mapped[list[EvidenceArtifactLink]] = relationship(
        "EvidenceArtifactLink", back_populates="evidence", cascade="all, delete-orphan"
    )


class AgentDecisionRow(Base):
    __tablename__ = "agent_decisions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    decision_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    targets_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    chosen_option: Mapped[str | None] = mapped_column(Text, nullable=True)
    alternatives_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="decisions")


class CritiqueRow(Base):
    __tablename__ = "critiques"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    critique_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    severity: Mapped[str] = mapped_column(String(32), nullable=False)
    target_kind: Mapped[str] = mapped_column(String(64), nullable=False)
    target_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved: Mapped[bool] = mapped_column(nullable=False, default=False)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="critiques")


class OpenQuestionRow(Base):
    __tablename__ = "open_questions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = _fk_inv()
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    related_hypothesis_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    answered_by_evidence_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="open_questions")


class ConclusionRow(Base):
    __tablename__ = "conclusions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    disposition: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    supporting_hypothesis_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    key_evidence_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    caveats_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    open_question_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    provenance_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship(
        "Investigation", back_populates="conclusions", foreign_keys=[investigation_id]
    )


# ---------------------------------------------------------------------------
# Association tables (FK integrity + artifact linkage to the existing table)
# ---------------------------------------------------------------------------


class EvidenceHypothesisLink(Base):
    __tablename__ = "evidence_hypothesis_links"
    __table_args__ = (
        UniqueConstraint("evidence_id", "hypothesis_id", name="uq_evidence_hypothesis"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    hypothesis_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("hypotheses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    direction: Mapped[str] = mapped_column(String(32), nullable=False)

    evidence: Mapped[EvidenceRow] = relationship("EvidenceRow", back_populates="hypothesis_links")


class EvidenceArtifactLink(Base):
    __tablename__ = "evidence_artifacts"
    __table_args__ = (UniqueConstraint("evidence_id", "artifact_id", name="uq_evidence_artifact"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evidence_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("evidence.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    evidence: Mapped[EvidenceRow] = relationship("EvidenceRow", back_populates="artifact_links")


class ExperimentResultArtifactLink(Base):
    __tablename__ = "experiment_result_artifacts"
    __table_args__ = (
        UniqueConstraint("experiment_result_id", "artifact_id", name="uq_experiment_result_artifact"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    experiment_result_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("experiment_results.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, index=True
    )

    experiment_result: Mapped[ExperimentResultRow] = relationship(
        "ExperimentResultRow", back_populates="artifact_links"
    )
    artifact: Mapped[Artifact] = relationship("Artifact")
