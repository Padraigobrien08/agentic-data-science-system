"""Stored case-level outcomes for supported evaluation runs."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.evaluation_run import EvaluationRun


class EvaluationCaseResult(Base):
    __tablename__ = "evaluation_case_results"
    __table_args__ = (
        # One row per case per run: ``replace_for_run`` deletes and reinserts wholesale,
        # and ``get_for_run_case`` looks a case up by this pair. Created by 012.
        UniqueConstraint("evaluation_run_id", "case_id", name="uq_evaluation_case_results_run_case"),
        # Control-plane listings filter a run's cases by each of these. Created by 012.
        Index("ix_evaluation_case_results_run_status", "evaluation_run_id", "status"),
        Index("ix_evaluation_case_results_run_input_mode", "evaluation_run_id", "input_mode"),
        Index("ix_evaluation_case_results_run_degradation", "evaluation_run_id", "degradation_class"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)
    evaluation_run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("evaluation_runs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    case_id: Mapped[str] = mapped_column(String(256), nullable=False)
    input_mode: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    degradation_class: Mapped[str] = mapped_column(String(64), nullable=False)
    run_goal: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    policy_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    observation_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    checks_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    artifacts_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
    latest_analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    latest_analysis_run_status: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
    )
    analysis_run_history_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)
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

    evaluation_run: Mapped[EvaluationRun] = relationship(
        "EvaluationRun",
        back_populates="case_results",
    )
