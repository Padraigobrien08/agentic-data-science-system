"""Run step lifecycle (uses :class:`~backend.repositories.run_step_repository.RunStepRepository`)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.json_merge import merge_dict_json
from backend.domain.status_transitions import can_transition_run_step, is_terminal_run_step
from backend.models.enums import RunStepStatus
from backend.models.run_step import RunStep
from backend.repositories.run_step_repository import RunStepRepository
from backend.services.exceptions import InvalidStatusTransition


class RunStepService:
    def __init__(
        self,
        session: Session,
        *,
        steps: RunStepRepository | None = None,
    ) -> None:
        self._steps = steps if steps is not None else RunStepRepository(session)

    def create(
        self,
        analysis_run_id: UUID,
        step_index: int,
        *,
        label: str | None = None,
        planned_tool_name: str | None = None,
        planner_tool_input_json: dict | list | None = None,
        meta_json: dict | list | None = None,
        step_id: UUID | None = None,
    ) -> RunStep:
        if self._steps.get_by_run_and_index(analysis_run_id, step_index) is not None:
            raise ValueError(
                f"Step index {step_index} already exists for analysis run {analysis_run_id}"
            )
        row = RunStep(
            id=step_id or uuid.uuid4(),
            analysis_run_id=analysis_run_id,
            step_index=step_index,
            status=RunStepStatus.pending,
            label=label,
            planned_tool_name=planned_tool_name,
            planner_tool_input_json=planner_tool_input_json,
            meta_json=meta_json,
        )
        self._steps.add(row)
        self._steps.flush()
        return row

    def get(self, step_id: UUID) -> RunStep | None:
        return self._steps.get(step_id)

    def require(self, step_id: UUID) -> RunStep:
        row = self.get(step_id)
        if row is None:
            raise KeyError(f"Run step not found: {step_id}")
        return row

    def get_by_index(self, analysis_run_id: UUID, step_index: int) -> RunStep | None:
        return self._steps.get_by_run_and_index(analysis_run_id, step_index)

    def list_for_analysis_run(self, analysis_run_id: UUID) -> list[RunStep]:
        return self._steps.list_for_analysis_run(analysis_run_id)

    def transition_status(
        self,
        step_id: UUID,
        target: RunStepStatus,
        *,
        detail: str | None = None,
    ) -> RunStep:
        row = self.require(step_id)
        if not can_transition_run_step(row.status, target):
            raise InvalidStatusTransition("RunStep", row.status, target)
        row.status = target
        if detail is not None:
            row.detail = detail
        now = datetime.now(timezone.utc)
        if target == RunStepStatus.running and row.started_at is None:
            row.started_at = now
        if is_terminal_run_step(target) and row.finished_at is None:
            row.finished_at = now
        self._steps.flush()
        return row

    def set_planner_tool_input(self, step_id: UUID, payload: dict | list | None) -> RunStep:
        row = self.require(step_id)
        row.planner_tool_input_json = payload
        self._steps.flush()
        return row

    def merge_planner_tool_input(self, step_id: UUID, patch: dict | None) -> RunStep:
        row = self.require(step_id)
        merged = merge_dict_json(
            row.planner_tool_input_json if isinstance(row.planner_tool_input_json, dict) else None,
            patch,
        )
        row.planner_tool_input_json = merged
        self._steps.flush()
        return row

    def merge_meta_json(self, step_id: UUID, patch: dict | None) -> RunStep:
        row = self.require(step_id)
        merged = merge_dict_json(
            row.meta_json if isinstance(row.meta_json, dict) else None,
            patch,
        )
        row.meta_json = merged
        self._steps.flush()
        return row
