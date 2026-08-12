"""Ordered step within an analysis run (planned or executed)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import RunStepStatus
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.analysis_run import AnalysisRun
    from backend.models.artifact import Artifact
    from backend.models.tool_call import ToolCall


class RunStep(Base):
    __tablename__ = "run_steps"
    __table_args__ = (
        UniqueConstraint(
            "analysis_run_id",
            "step_index",
            name="uq_run_steps_analysis_run_id_step_index",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    step_index: Mapped[int] = mapped_column(Integer, nullable=False, index=True)

    status: Mapped[RunStepStatus] = mapped_column(
        str_enum_column(RunStepStatus, name="run_step_status"),
        nullable=False,
        default=RunStepStatus.pending,
        server_default=RunStepStatus.pending.value,
        index=True,
    )

    label: Mapped[str | None] = mapped_column(String(512), nullable=True)
    planned_tool_name: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    planner_tool_input_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="PlannedStep.tool_input snapshot",
    )
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

    analysis_run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="run_steps")
    tool_call: Mapped[ToolCall | None] = relationship(
        "ToolCall",
        back_populates="run_step",
        uselist=False,
        cascade="all, delete-orphan",
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        "Artifact",
        back_populates="run_step",
    )
