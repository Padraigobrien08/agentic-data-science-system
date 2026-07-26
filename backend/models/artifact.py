"""Persisted artifact metadata (bytes live in object store or filesystem)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import ArtifactKind
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.analysis_run import AnalysisRun
    from backend.models.evaluation_run import EvaluationRun
    from backend.models.run_step import RunStep


class Artifact(Base):
    __tablename__ = "artifacts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    evaluation_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    run_step_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("run_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role_key: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        index=True,
        doc="Logical role e.g. panel_csv, report_md",
    )
    kind: Mapped[ArtifactKind] = mapped_column(
        str_enum_column(ArtifactKind, name="artifact_kind"),
        nullable=False,
        default=ArtifactKind.other,
        index=True,
    )

    storage_uri: Mapped[str] = mapped_column(
        String(2048),
        nullable=False,
        doc="Backend-specific locator (path, s3://, etc.)",
    )
    mime_type: Mapped[str | None] = mapped_column(String(256), nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    meta_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    blob_deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        doc="When set, the blob was intentionally pruned by retention policy.",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    analysis_run: Mapped[AnalysisRun | None] = relationship("AnalysisRun", back_populates="artifacts")
    evaluation_run: Mapped[EvaluationRun | None] = relationship(
        "EvaluationRun",
        back_populates="artifacts",
    )
    run_step: Mapped[RunStep | None] = relationship("RunStep", back_populates="artifacts")
