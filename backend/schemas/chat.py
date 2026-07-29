"""Conversation / chat-message request and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import ChatMessageRole, ChatMessageStatus
from backend.schemas.common import OrmSchema, TimestampedRead


class ConversationCreate(OrmSchema):
    title: str | None = Field(default=None, max_length=256)


class ConversationUpdate(OrmSchema):
    title: str | None = Field(default=None, max_length=256)
    archived_at: datetime | None = None


class ChatMessageCreate(OrmSchema):
    role: ChatMessageRole
    content: str | None = None
    status: ChatMessageStatus = ChatMessageStatus.complete
    client_request_id: str | None = Field(default=None, max_length=64)
    analysis_run_id: UUID | None = None
    meta_json: dict | list | None = None
    error_summary: str | None = None


class ChatMessageRead(TimestampedRead):
    id: UUID
    conversation_id: UUID
    role: ChatMessageRole
    status: ChatMessageStatus
    content: str | None
    error_summary: str | None
    client_request_id: str | None
    analysis_run_id: UUID | None
    meta_json: dict | list | None = None


class ConversationRead(TimestampedRead):
    id: UUID
    project_id: UUID
    owner_user_id: UUID | None
    title: str | None
    last_message_at: datetime | None
    archived_at: datetime | None


class ConversationDetailRead(ConversationRead):
    messages: list[ChatMessageRead] = Field(default_factory=list)
