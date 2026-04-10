"""Tool call (MCP) schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import Field

from backend.models.enums import ToolCallMcpStatus
from backend.schemas.common import OrmSchema, TimestampedRead


class ToolCallCreate(OrmSchema):
    run_step_id: UUID
    tool_name: str = Field(max_length=128)
    request_params_json: dict | list | None = None


class ToolCallUpdate(OrmSchema):
    mcp_status: ToolCallMcpStatus | None = None
    response_envelope_json: dict | list | None = None
    error_detail: str | None = None
    panel_row_count: int | None = None
    feature_row_count: int | None = None
    anomaly_count: int | None = None
    report_character_count: int | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None


class ToolCallRead(TimestampedRead):
    id: UUID
    analysis_run_id: UUID
    run_step_id: UUID
    tool_name: str
    mcp_status: ToolCallMcpStatus
    request_params_json: dict | list | None = None
    response_envelope_json: dict | list | None = None
    error_detail: str | None = None
    panel_row_count: int | None = None
    feature_row_count: int | None = None
    anomaly_count: int | None = None
    report_character_count: int | None = None
    started_at: datetime | None
    finished_at: datetime | None
