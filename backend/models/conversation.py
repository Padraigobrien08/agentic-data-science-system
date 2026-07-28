"""A durable chat thread within a project (many conversations per project)."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base

if TYPE_CHECKING:
    from backend.models.chat_message import ChatMessage
    from backend.models.project import Project
    from backend.models.user import User


class Conversation(Base):
    """One visible chat thread. Owns an ordered list of :class:`ChatMessage` rows.

    A conversation belongs to a project (the workspace/scope container) and is the
    stable thread identity — creating a new chat inserts a new row here instead of
    reusing the project, so prior threads remain visible.
    """

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    title: Mapped[str | None] = mapped_column(String(256), nullable=True)

    last_message_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

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

    project: Mapped[Project] = relationship("Project", back_populates="conversations")
    owner: Mapped[User | None] = relationship("User")
    messages: Mapped[list[ChatMessage]] = relationship(
        "ChatMessage",
        back_populates="conversation",
        order_by="ChatMessage.created_at",
        cascade="all, delete-orphan",
    )
