"""Queued background execution job for an analysis run (one row per enqueue)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import RunExecutionJobStatus
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.analysis_run import AnalysisRun


class RunExecutionJob(Base):
    __tablename__ = "run_execution_jobs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    analysis_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[RunExecutionJobStatus] = mapped_column(
        str_enum_column(RunExecutionJobStatus, name="run_execution_job_status"),
        nullable=False,
        default=RunExecutionJobStatus.pending,
        index=True,
    )

    overrides_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Optional execute overrides: tickers, analysis_goal, refresh",
    )

    error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)

    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    analysis_run: Mapped[AnalysisRun] = relationship("AnalysisRun", back_populates="execution_jobs")
