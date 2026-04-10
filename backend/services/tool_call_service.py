"""Tool call (MCP) records (uses :class:`~backend.repositories.tool_call_repository.ToolCallRepository`)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.json_merge import merge_dict_json
from backend.domain.status_transitions import can_transition_tool_mcp_status
from backend.models.enums import ToolCallMcpStatus
from backend.models.tool_call import ToolCall
from backend.repositories.tool_call_repository import ToolCallRepository
from backend.services.exceptions import InvalidStatusTransition


class ToolCallService:
    def __init__(
        self,
        session: Session,
        *,
        tool_calls: ToolCallRepository | None = None,
    ) -> None:
        self._tc = tool_calls if tool_calls is not None else ToolCallRepository(session)

    def create(
        self,
        analysis_run_id: UUID,
        run_step_id: UUID,
        tool_name: str,
        *,
        request_params_json: dict | list | None = None,
        mcp_status: ToolCallMcpStatus = ToolCallMcpStatus.success,
        tool_call_id: UUID | None = None,
    ) -> ToolCall:
        if self._tc.get_by_run_step_id(run_step_id) is not None:
            raise ValueError(f"Tool call already exists for run_step_id={run_step_id}")
        row = ToolCall(
            id=tool_call_id or uuid.uuid4(),
            analysis_run_id=analysis_run_id,
            run_step_id=run_step_id,
            tool_name=tool_name,
            mcp_status=mcp_status,
            request_params_json=request_params_json,
        )
        self._tc.add(row)
        self._tc.flush()
        return row

    def get(self, tool_call_id: UUID) -> ToolCall | None:
        return self._tc.get(tool_call_id)

    def require(self, tool_call_id: UUID) -> ToolCall:
        row = self.get(tool_call_id)
        if row is None:
            raise KeyError(f"Tool call not found: {tool_call_id}")
        return row

    def get_for_run_step(self, run_step_id: UUID) -> ToolCall | None:
        return self._tc.get_by_run_step_id(run_step_id)

    def list_for_analysis_run(self, analysis_run_id: UUID) -> list[ToolCall]:
        return self._tc.list_for_analysis_run(analysis_run_id)

    def start_execution(self, tool_call_id: UUID) -> ToolCall:
        """Mark start time before MCP dispatch (idempotent if already set)."""
        row = self.require(tool_call_id)
        if row.started_at is None:
            row.started_at = datetime.now(timezone.utc)
        self._tc.flush()
        return row

    def record_response(
        self,
        tool_call_id: UUID,
        mcp_status: ToolCallMcpStatus,
        *,
        response_envelope_json: dict | list | None = None,
        error_detail: str | None = None,
        panel_row_count: int | None = None,
        feature_row_count: int | None = None,
        anomaly_count: int | None = None,
        report_character_count: int | None = None,
        allow_rewrite: bool = False,
    ) -> ToolCall:
        row = self.require(tool_call_id)
        finalized = row.response_envelope_json is not None
        if not can_transition_tool_mcp_status(
            row.mcp_status,
            mcp_status,
            finalized=finalized,
            allow_rewrite=allow_rewrite,
        ):
            raise InvalidStatusTransition("ToolCall.mcp_status", row.mcp_status, mcp_status)
        if (
            finalized
            and not allow_rewrite
            and response_envelope_json is not None
            and response_envelope_json != row.response_envelope_json
        ):
            raise ValueError("Cannot replace response_envelope_json without allow_rewrite=True")
        row.mcp_status = mcp_status
        if response_envelope_json is not None:
            row.response_envelope_json = response_envelope_json
        if error_detail is not None:
            row.error_detail = error_detail
        if panel_row_count is not None:
            row.panel_row_count = panel_row_count
        if feature_row_count is not None:
            row.feature_row_count = feature_row_count
        if anomaly_count is not None:
            row.anomaly_count = anomaly_count
        if report_character_count is not None:
            row.report_character_count = report_character_count
        row.finished_at = datetime.now(timezone.utc)
        self._tc.flush()
        return row

    def merge_request_params(self, tool_call_id: UUID, patch: dict | None) -> ToolCall:
        row = self.require(tool_call_id)
        merged = merge_dict_json(
            row.request_params_json if isinstance(row.request_params_json, dict) else None,
            patch,
        )
        row.request_params_json = merged
        self._tc.flush()
        return row
