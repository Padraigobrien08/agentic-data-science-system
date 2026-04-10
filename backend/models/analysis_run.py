"""One end-to-end analysis / orchestration execution (EDGAR pipeline or equivalent)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import AnalysisRunStatus
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.artifact import Artifact
    from backend.models.model_call import ModelCall
    from backend.models.project import Project
    from backend.models.run_step import RunStep
    from backend.models.tool_call import ToolCall
    from backend.models.user import User


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    correlation_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        unique=True,
        index=True,
        doc="External id e.g. OrchestrationOutput.run_id",
    )

    status: Mapped[AnalysisRunStatus] = mapped_column(
        str_enum_column(AnalysisRunStatus, name="analysis_run_status"),
        nullable=False,
        default=AnalysisRunStatus.pending,
        index=True,
    )

    orchestration_goal_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_payload_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="OrchestrationInput and related request context",
    )
    output_payload_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="OrchestrationOutput snapshot",
    )
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    meta_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    project: Mapped[Project] = relationship("Project", back_populates="analysis_runs")
    initiated_by_user: Mapped[User | None] = relationship(
        "User",
        back_populates="analysis_runs_initiated",
    )
    run_steps: Mapped[list[RunStep]] = relationship(
        "RunStep",
        back_populates="analysis_run",
        order_by="RunStep.step_index",
        cascade="all, delete-orphan",
    )
    tool_calls: Mapped[list[ToolCall]] = relationship(
        "ToolCall",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        "Artifact",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
    model_calls: Mapped[list[ModelCall]] = relationship(
        "ModelCall",
        back_populates="analysis_run",
        cascade="all, delete-orphan",
    )
