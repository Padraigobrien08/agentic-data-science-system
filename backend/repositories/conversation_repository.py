"""Persistence for :class:`~backend.models.conversation.Conversation` (no business rules)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.conversation import Conversation


class ConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def get(self, conversation_id: UUID) -> Conversation | None:
        return self._session.get(Conversation, conversation_id)

    def list_for_project(self, project_id: UUID, *, include_archived: bool = False) -> list[Conversation]:
        """Conversations in a project, most recently active first."""
        stmt = select(Conversation).where(Conversation.project_id == project_id)
        if not include_archived:
            stmt = stmt.where(Conversation.archived_at.is_(None))
        # Active threads first (by last message), then newest created as a tiebreaker.
        stmt = stmt.order_by(
            Conversation.last_message_at.desc().nulls_last(),
            Conversation.created_at.desc(),
        )
        return list(self._session.scalars(stmt).all())

    def add(self, row: Conversation) -> Conversation:
        self._session.add(row)
        return row

    def delete(self, row: Conversation) -> None:
        self._session.delete(row)
