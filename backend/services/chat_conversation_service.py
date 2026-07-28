"""Durable chat threads and messages.

Business rules for the conversation/message layer that sits between a project and its
analysis runs: creating threads, appending turns, deriving a thread title from the first
user prompt, and keeping ``last_message_at`` fresh for history ordering. Services flush
and return rows; the caller (route handler) owns the commit.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.chat_message import ChatMessage
from backend.models.conversation import Conversation
from backend.models.enums import ChatMessageRole, ChatMessageStatus
from backend.repositories.chat_message_repository import ChatMessageRepository
from backend.repositories.conversation_repository import ConversationRepository

_TITLE_MAX_LEN = 120


def _derive_title(content: str | None) -> str | None:
    if not content:
        return None
    text = " ".join(content.split())
    if not text:
        return None
    if len(text) <= _TITLE_MAX_LEN:
        return text
    return text[: _TITLE_MAX_LEN - 1].rstrip() + "…"


class ChatConversationService:
    def __init__(
        self,
        session: Session,
        *,
        conversations: ConversationRepository | None = None,
        messages: ChatMessageRepository | None = None,
    ) -> None:
        self._conversations = conversations or ConversationRepository(session)
        self._messages = messages or ChatMessageRepository(session)

    # -- conversations -----------------------------------------------------

    def create_conversation(
        self,
        project_id: UUID,
        *,
        owner_user_id: UUID | None = None,
        title: str | None = None,
    ) -> Conversation:
        row = Conversation(
            id=uuid.uuid4(),
            project_id=project_id,
            owner_user_id=owner_user_id,
            title=_derive_title(title),
        )
        self._conversations.add(row)
        self._conversations.flush()
        return row

    def get_conversation(self, conversation_id: UUID) -> Conversation | None:
        return self._conversations.get(conversation_id)

    def list_conversations(
        self,
        project_id: UUID,
        *,
        include_archived: bool = False,
    ) -> list[Conversation]:
        return self._conversations.list_for_project(project_id, include_archived=include_archived)

    def update_conversation(
        self,
        conversation: Conversation,
        *,
        title: str | None = None,
        archived_at: datetime | None = None,
        clear_archived: bool = False,
    ) -> Conversation:
        if title is not None:
            conversation.title = _derive_title(title)
        if clear_archived:
            conversation.archived_at = None
        elif archived_at is not None:
            conversation.archived_at = archived_at
        self._conversations.add(conversation)
        self._conversations.flush()
        return conversation

    def delete_conversation(self, conversation: Conversation) -> None:
        self._conversations.delete(conversation)
        self._conversations.flush()

    # -- messages ----------------------------------------------------------

    def add_message(
        self,
        conversation: Conversation,
        *,
        role: ChatMessageRole,
        content: str | None = None,
        status: ChatMessageStatus = ChatMessageStatus.complete,
        client_request_id: str | None = None,
        analysis_run_id: UUID | None = None,
        meta_json: dict | list | None = None,
        error_summary: str | None = None,
    ) -> ChatMessage:
        row = ChatMessage(
            id=uuid.uuid4(),
            conversation_id=conversation.id,
            role=role,
            status=status,
            content=content,
            client_request_id=client_request_id,
            analysis_run_id=analysis_run_id,
            meta_json=meta_json,
            error_summary=error_summary,
            # Microsecond stamp so ordering is stable even on SQLite, whose
            # ``func.now()`` only has 1-second resolution.
            created_at=datetime.now(timezone.utc),
        )
        self._messages.add(row)
        self._messages.flush()
        # Keep the thread ordered by real activity and titled from its first prompt.
        conversation.last_message_at = row.created_at
        if conversation.title is None and role == ChatMessageRole.user:
            conversation.title = _derive_title(content)
        self._conversations.add(conversation)
        self._conversations.flush()
        return row

    def list_messages(self, conversation_id: UUID) -> list[ChatMessage]:
        return self._messages.list_for_conversation(conversation_id)
