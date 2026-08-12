"""Benchmark / evaluation suite execution."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import EvaluationRunStatus
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.artifact import Artifact
    from backend.models.evaluation_case_result import EvaluationCaseResult
    from backend.models.model_call import ModelCall
    from backend.models.project import Project
    from backend.models.user import User


class EvaluationRun(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    initiated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    suite_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    suite_manifest_path: Mapped[str | None] = mapped_column(String(1024), nullable=True)

    status: Mapped[EvaluationRunStatus] = mapped_column(
        str_enum_column(EvaluationRunStatus, name="evaluation_run_status"),
        nullable=False,
        default=EvaluationRunStatus.pending,
        server_default=EvaluationRunStatus.pending.value,
        index=True,
    )

    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    results_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Optional embedded per-case results or pointers",
    )
    config_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

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

    project: Mapped[Project | None] = relationship("Project", back_populates="evaluation_runs")
    initiated_by_user: Mapped[User | None] = relationship(
        "User",
        back_populates="evaluation_runs_initiated",
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        "Artifact",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
    )
    model_calls: Mapped[list[ModelCall]] = relationship(
        "ModelCall",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
    )
    case_results: Mapped[list[EvaluationCaseResult]] = relationship(
        "EvaluationCaseResult",
        back_populates="evaluation_run",
        cascade="all, delete-orphan",
        order_by="EvaluationCaseResult.case_id",
    )
