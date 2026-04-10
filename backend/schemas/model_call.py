"""Model (LLM) invocation schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import ModelCallStatus
from backend.schemas.common import OrmSchema, TimestampedRead


class ModelCallCreate(OrmSchema):
    provider: str = Field(max_length=64)
    model_name: str = Field(max_length=256)
    analysis_run_id: UUID | None = None
    evaluation_run_id: UUID | None = None
    tool_call_id: UUID | None = None
    request_payload_json: dict | list | None = None


class ModelCallUpdate(OrmSchema):
    status: ModelCallStatus | None = None
    prompt_tokens: int | None = Field(default=None, ge=0)
    completion_tokens: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    response_payload_json: dict | list | None = None
    error_detail: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ModelCallRead(TimestampedRead):
    id: UUID
    analysis_run_id: UUID | None
    evaluation_run_id: UUID | None
    tool_call_id: UUID | None
    provider: str
    model_name: str
    status: ModelCallStatus
    prompt_tokens: int | None
    completion_tokens: int | None
    latency_ms: int | None
    request_payload_json: dict | list | None = None
    response_payload_json: dict | list | None = None
    error_detail: str | None = None
    started_at: datetime | None
    finished_at: datetime | None
