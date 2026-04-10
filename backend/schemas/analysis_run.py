"""Analysis run request/response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import AnalysisRunStatus
from backend.schemas.common import OrmSchema, TimestampedRead


class AnalysisRunCreate(OrmSchema):
    project_id: UUID
    correlation_id: str | None = Field(default=None, max_length=64)
    orchestration_goal_text: str | None = None
    input_payload_json: dict | list | None = None
    meta_json: dict | list | None = None


class AnalysisRunUpdate(OrmSchema):
    status: AnalysisRunStatus | None = None
    output_payload_json: dict | list | None = None
    error_summary: str | None = None
    meta_json: dict | list | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class AnalysisRunRead(TimestampedRead):
    id: UUID
    project_id: UUID
    initiated_by_user_id: UUID | None
    correlation_id: str | None
    status: AnalysisRunStatus
    orchestration_goal_text: str | None
    input_payload_json: dict | list | None = None
    output_payload_json: dict | list | None = None
    error_summary: str | None = None
    meta_json: dict | list | None = None
    started_at: datetime | None
    finished_at: datetime | None
