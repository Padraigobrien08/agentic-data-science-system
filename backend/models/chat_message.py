"""One durable message in a conversation; assistant turns point at their run."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.base import Base
from backend.models.enums import ChatMessageRole, ChatMessageStatus
from backend.models.types import str_enum_column

if TYPE_CHECKING:
    from backend.models.analysis_run import AnalysisRun
    from backend.models.conversation import Conversation


class ChatMessage(Base):
    """Durable chat surface. Deterministic evidence stays on the linked run.

    An assistant message begins ``pending`` and is filled in once its analysis run
    completes: ``content`` gets the narrative, ``analysis_run_id`` links the run, and
    ``meta_json`` caches the rendered answer card so history loads need not re-derive it.
    """

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4)

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    analysis_run_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("analysis_runs.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role: Mapped[ChatMessageRole] = mapped_column(
        str_enum_column(ChatMessageRole, name="chat_message_role"),
        nullable=False,
    )
    status: Mapped[ChatMessageStatus] = mapped_column(
        str_enum_column(ChatMessageStatus, name="chat_message_status"),
        nullable=False,
        default=ChatMessageStatus.complete,
    )

    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    client_request_id: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        doc="Client-generated id for optimistic reconciliation / idempotency.",
    )
    meta_json: Mapped[dict | list | None] = mapped_column(
        JSON,
        nullable=True,
        doc="Cached answer card, routing reason, rewrite suggestions, delivery mode.",
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

    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")
    analysis_run: Mapped[AnalysisRun | None] = relationship("AnalysisRun")
