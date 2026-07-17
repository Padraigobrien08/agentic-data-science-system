"""
Investigation root cluster — persistence for the generalized investigation model.

Additive to the existing schema: an :class:`Investigation` optionally links to an
existing ``analysis_runs`` row (compatibility layer) and to ``projects`` / ``users``.
Optimistic concurrency is enforced via ``state_version`` (SQLAlchemy version id).
The append-only :class:`InvestigationStateEvent` log and durable
:class:`OrchestrationCheckpoint` snapshots make history inspectable and enable
exact-state resume.
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
from backend.models.enums_investigation import InvestigationOrigin
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.investigation_entities import (
        AgentDecisionRow,
        ConclusionRow,
        CritiqueRow,
        EvidenceRow,
        ExperimentRequestRow,
        ExperimentResultRow,
        HypothesisRow,
        ObservationRow,
        OpenQuestionRow,
    )


class Investigation(Base):
    """Durable root of one generalized investigation."""

    __tablename__ = "investigations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, unique=True, index=True,
        doc="Stable domain-layer Investigation id (e.g. inv_...).",
    )

    # Optional links reusing existing identity (all nullable, non-destructive).
    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("projects.id", ondelete="SET NULL"), nullable=True, index=True
    )
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
        unique=True,
        index=True,
        doc="Canonical/legacy run this investigation represents; run stays source of truth for legacy origin.",
    )

    origin: Mapped[InvestigationOrigin] = mapped_column(
        str_enum_column(InvestigationOrigin, name="investigation_origin"),
        nullable=False,
        default=InvestigationOrigin.native,
        index=True,
    )
    # Domain lifecycle status stored as its string value (validated at domain boundary).
    status: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")

    # Optimistic concurrency control: SQLAlchemy manages this on every flush.
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    goal_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    budget_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    termination_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    current_conclusion_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("conclusions.id", ondelete="SET NULL"), nullable=True
    )
    reproducibility_manifest_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("reproducibility_manifests.id", ondelete="SET NULL"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __mapper_args__ = {"version_id_col": state_version}

    datasets: Mapped[list[InvestigationDataset]] = relationship(
        "InvestigationDataset", back_populates="investigation", cascade="all, delete-orphan"
    )
    events: Mapped[list[InvestigationStateEvent]] = relationship(
        "InvestigationStateEvent", back_populates="investigation",
        cascade="all, delete-orphan", order_by="InvestigationStateEvent.sequence",
    )
    checkpoints: Mapped[list[OrchestrationCheckpoint]] = relationship(
        "OrchestrationCheckpoint", back_populates="investigation",
        cascade="all, delete-orphan", order_by="OrchestrationCheckpoint.sequence",
    )
    hypotheses: Mapped[list[HypothesisRow]] = relationship(
        "HypothesisRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    evidence: Mapped[list[EvidenceRow]] = relationship(
        "EvidenceRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    experiment_requests: Mapped[list[ExperimentRequestRow]] = relationship(
        "ExperimentRequestRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    experiment_results: Mapped[list[ExperimentResultRow]] = relationship(
        "ExperimentResultRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    observations: Mapped[list[ObservationRow]] = relationship(
        "ObservationRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    decisions: Mapped[list[AgentDecisionRow]] = relationship(
        "AgentDecisionRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    critiques: Mapped[list[CritiqueRow]] = relationship(
        "CritiqueRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    open_questions: Mapped[list[OpenQuestionRow]] = relationship(
        "OpenQuestionRow", back_populates="investigation", cascade="all, delete-orphan"
    )
    conclusions: Mapped[list[ConclusionRow]] = relationship(
        "ConclusionRow", back_populates="investigation",
        cascade="all, delete-orphan", foreign_keys="ConclusionRow.investigation_id",
    )


class InvestigationDataset(Base):
    """A dataset reference bound to an investigation (DatasetReference + manifest)."""

    __tablename__ = "investigation_datasets"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    domain_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    data_source_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    locator: Mapped[str | None] = mapped_column(Text, nullable=True)
    content_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    manifest_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="datasets")


class ReproducibilityManifestRow(Base):
    """Persisted reproducibility manifest (tool/prompt versions, model config, seed, env)."""

    __tablename__ = "reproducibility_manifests"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    domain_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    code_version: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tool_versions_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    prompt_versions_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    model_config_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    random_seed: Mapped[int | None] = mapped_column(Integer, nullable=True)
    dataset_reference_ids_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    parameters_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    environment_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())


class InvestigationStateEvent(Base):
    """Append-only log of state changes (per-investigation monotonic sequence)."""

    __tablename__ = "investigation_state_events"
    __table_args__ = (UniqueConstraint("investigation_id", "sequence", name="uq_state_event_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_kind: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="events")


class OrchestrationCheckpoint(Base):
    """Durable full-state snapshot enabling exact resume (per-investigation sequence)."""

    __tablename__ = "orchestration_checkpoints"
    __table_args__ = (UniqueConstraint("investigation_id", "sequence", name="uq_checkpoint_seq"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    label: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state_json: Mapped[dict | list] = mapped_column(JSON, nullable=False, doc="Full serialized InvestigationState.")
    schema_version: Mapped[str] = mapped_column(String(32), nullable=False, default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    investigation: Mapped[Investigation] = relationship("Investigation", back_populates="checkpoints")
