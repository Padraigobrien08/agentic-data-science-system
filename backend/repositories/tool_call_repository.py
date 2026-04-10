"""Persistence for :class:`~backend.models.tool_call.ToolCall`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.tool_call import ToolCall


class ToolCallRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def get(self, tool_call_id: UUID) -> ToolCall | None:
        return self._session.get(ToolCall, tool_call_id)

    def get_by_run_step_id(self, run_step_id: UUID) -> ToolCall | None:
        return self._session.scalar(select(ToolCall).where(ToolCall.run_step_id == run_step_id))

    def list_for_analysis_run(self, analysis_run_id: UUID) -> list[ToolCall]:
        return list(
            self._session.scalars(
                select(ToolCall)
                .where(ToolCall.analysis_run_id == analysis_run_id)
                .order_by(ToolCall.created_at)
            ).all()
        )

    def add(self, row: ToolCall) -> ToolCall:
        self._session.add(row)
        return row
