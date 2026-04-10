"""Run step schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import RunStepStatus
from backend.schemas.common import OrmSchema, TimestampedRead


class RunStepCreate(OrmSchema):
    step_index: int = Field(ge=0)
    label: str | None = Field(default=None, max_length=512)
    planned_tool_name: str | None = Field(default=None, max_length=128)
    planner_tool_input_json: dict | list | None = None
    meta_json: dict | list | None = None


class RunStepUpdate(OrmSchema):
    status: RunStepStatus | None = None
    detail: str | None = None
    meta_json: dict | list | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class RunStepRead(TimestampedRead):
    id: UUID
    analysis_run_id: UUID
    step_index: int
    status: RunStepStatus
    label: str | None
    planned_tool_name: str | None
    detail: str | None
    planner_tool_input_json: dict | list | None = None
    meta_json: dict | list | None = None
    started_at: datetime | None
    finished_at: datetime | None
