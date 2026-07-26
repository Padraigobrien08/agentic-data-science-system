"""Single MCP (or tool) invocation, usually one-to-one with a run step."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import ToolCallMcpStatus
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.analysis_run import AnalysisRun
    from backend.models.model_call import ModelCall
    from backend.models.run_step import RunStep


class ToolCall(Base):
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    run_step_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("run_steps.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )

    tool_name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    mcp_status: Mapped[ToolCallMcpStatus] = mapped_column(
        str_enum_column(ToolCallMcpStatus, name="tool_call_mcp_status"),
        nullable=False,
        default=ToolCallMcpStatus.success,
        index=True,
    )

    request_params_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    response_envelope_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Full MCP ToolResponseEnvelope (model_dump)",
    )
    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    panel_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feature_row_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anomaly_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    report_character_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

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

    analysis_run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="tool_calls")
    run_step: Mapped[RunStep] = relationship("RunStep", back_populates="tool_call")
    model_calls: Mapped[list[ModelCall]] = relationship(
        "ModelCall",
        back_populates="tool_call",
        cascade="all, delete-orphan",
    )
