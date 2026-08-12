"""Application user (auth and attribution)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, String, Uuid, false, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import UserAccessTier
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.analysis_run import AnalysisRun
    from backend.models.evaluation_run import EvaluationRun
    from backend.models.project import Project


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # ``true()``/``false()`` render as TRUE/FALSE on Postgres and 1/0 on SQLite, matching
    # what 002 and 008 wrote; a literal would be rejected by one dialect or the other.
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default=true()
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    preferences_json: Mapped[dict | list | None] = mapped_column(JSON, nullable=True)

    # Spend entitlement, not a permission: it decides which engine a run may use and which
    # budget ceiling applies. Existing rows backfill to ``standard`` (the deterministic
    # engine), so enabling the agentic flag cannot retroactively grant anyone the loop.
    access_tier: Mapped[UserAccessTier] = mapped_column(
        str_enum_column(UserAccessTier, name="user_access_tier"),
        nullable=False,
        default=UserAccessTier.standard,
        server_default=UserAccessTier.standard.value,
        index=True,
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

    projects: Mapped[list[Project]] = relationship(
        "Project",
        back_populates="owner",
        cascade="all, delete-orphan",
    )
    analysis_runs_initiated: Mapped[list[AnalysisRun]] = relationship(
        "AnalysisRun",
        back_populates="initiated_by_user",
    )
    evaluation_runs_initiated: Mapped[list[EvaluationRun]] = relationship(
        "EvaluationRun",
        back_populates="initiated_by_user",
    )
