"""Durable chat threads: create/list/read/update/delete conversations and append messages.

The Next.js server action still drives run creation; these endpoints persist the visible
chat surface (threads + turns) and link assistant turns to the run that produced them.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from backend.api.access_checks import (
    require_analysis_run_owned,
    require_conversation_owned,
    require_project_owned,
)
from backend.api.auth_deps import CurrentUserDep
from backend.api.deps import ChatConversationServiceDep, DbSession
from backend.models.conversation import Conversation
from backend.schemas.chat import (
    ChatMessageCreate,
    ChatMessageRead,
    ConversationCreate,
    ConversationDetailRead,
    ConversationRead,
    ConversationUpdate,
)

router = APIRouter(tags=["conversations"])


@router.post(
    "/projects/{project_id}/conversations",
    response_model=ConversationRead,
    status_code=201,
)
def create_conversation(
    project_id: UUID,
    body: ConversationCreate,
    db: DbSession,
    user: CurrentUserDep,
    chat: ChatConversationServiceDep,
) -> Conversation:
    require_project_owned(db, project_id, user.id)
    row = chat.create_conversation(project_id, owner_user_id=user.id, title=body.title)
    db.commit()
    db.refresh(row)
    return row


@router.get(
    "/projects/{project_id}/conversations",
    response_model=list[ConversationRead],
)
def list_conversations(
    project_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    chat: ChatConversationServiceDep,
) -> list[Conversation]:
    require_project_owned(db, project_id, user.id)
    return chat.list_conversations(project_id)


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailRead)
def get_conversation(
    conversation_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> Conversation:
    return require_conversation_owned(db, conversation_id, user.id)


@router.patch("/conversations/{conversation_id}", response_model=ConversationRead)
def update_conversation(
    conversation_id: UUID,
    body: ConversationUpdate,
    db: DbSession,
    user: CurrentUserDep,
    chat: ChatConversationServiceDep,
) -> Conversation:
    row = require_conversation_owned(db, conversation_id, user.id)
    chat.update_conversation(row, title=body.title, archived_at=body.archived_at)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/conversations/{conversation_id}", status_code=204)
def delete_conversation(
    conversation_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    chat: ChatConversationServiceDep,
) -> None:
    row = require_conversation_owned(db, conversation_id, user.id)
    chat.delete_conversation(row)
    db.commit()


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=ChatMessageRead,
    status_code=201,
)
def append_message(
    conversation_id: UUID,
    body: ChatMessageCreate,
    db: DbSession,
    user: CurrentUserDep,
    chat: ChatConversationServiceDep,
) -> ChatMessageRead:
    conversation = require_conversation_owned(db, conversation_id, user.id)
    # An assistant turn may reference a run; only accept runs the caller owns.
    if body.analysis_run_id is not None:
        require_analysis_run_owned(db, body.analysis_run_id, user.id)
    row = chat.add_message(
        conversation,
        role=body.role,
        content=body.content,
        status=body.status,
        client_request_id=body.client_request_id,
        analysis_run_id=body.analysis_run_id,
        meta_json=body.meta_json,
        error_summary=body.error_summary,
    )
    db.commit()
    db.refresh(row)
    return ChatMessageRead.model_validate(row)
