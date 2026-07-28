"""Persistence for :class:`~backend.models.chat_message.ChatMessage` (no business rules)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.chat_message import ChatMessage


class ChatMessageRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def get(self, message_id: UUID) -> ChatMessage | None:
        return self._session.get(ChatMessage, message_id)

    def list_for_conversation(self, conversation_id: UUID) -> list[ChatMessage]:
        """All messages in a conversation, oldest first (chat order)."""
        return list(
            self._session.scalars(
                select(ChatMessage)
                .where(ChatMessage.conversation_id == conversation_id)
                .order_by(ChatMessage.created_at, ChatMessage.id)
            ).all()
        )

    def get_by_client_request_id(
        self,
        conversation_id: UUID,
        client_request_id: str,
    ) -> ChatMessage | None:
        return self._session.scalar(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation_id)
            .where(ChatMessage.client_request_id == client_request_id)
            .order_by(ChatMessage.created_at.desc())
        )

    def add(self, row: ChatMessage) -> ChatMessage:
        self._session.add(row)
        return row
