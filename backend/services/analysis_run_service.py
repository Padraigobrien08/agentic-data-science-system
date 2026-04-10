"""Analysis run lifecycle and JSON payloads (uses :class:`~backend.repositories.analysis_run_repository.AnalysisRunRepository`)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.json_merge import merge_dict_json
from backend.domain.status_transitions import (
    can_transition_analysis_run,
    is_terminal_analysis_run,
)
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.repositories.analysis_run_repository import AnalysisRunRepository
from backend.services.exceptions import InvalidStatusTransition


class AnalysisRunService:
    def __init__(
        self,
        session: Session,
        *,
        runs: AnalysisRunRepository | None = None,
    ) -> None:
        self._runs = runs if runs is not None else AnalysisRunRepository(session)

    def create(
        self,
        project_id: UUID,
        *,
        initiated_by_user_id: UUID | None = None,
        correlation_id: str | None = None,
        orchestration_goal_text: str | None = None,
        input_payload_json: dict | list | None = None,
        meta_json: dict | list | None = None,
        run_id: UUID | None = None,
    ) -> AnalysisRun:
        row = AnalysisRun(
            id=run_id or uuid.uuid4(),
            project_id=project_id,
            initiated_by_user_id=initiated_by_user_id,
            correlation_id=correlation_id,
            status=AnalysisRunStatus.pending,
            orchestration_goal_text=orchestration_goal_text,
            input_payload_json=input_payload_json,
            meta_json=meta_json,
        )
        self._runs.add(row)
        self._runs.flush()
        return row

    def get(self, run_id: UUID) -> AnalysisRun | None:
        return self._runs.get(run_id)

    def require(self, run_id: UUID) -> AnalysisRun:
        row = self.get(run_id)
        if row is None:
            raise KeyError(f"Analysis run not found: {run_id}")
        return row

    def get_by_correlation_id(self, correlation_id: str) -> AnalysisRun | None:
        return self._runs.get_by_correlation_id(correlation_id)

    def list_for_project(self, project_id: UUID) -> list[AnalysisRun]:
        return self._runs.list_for_project(project_id)

    def transition_status(self, run_id: UUID, target: AnalysisRunStatus) -> AnalysisRun:
        row = self.require(run_id)
        if not can_transition_analysis_run(row.status, target):
            raise InvalidStatusTransition("AnalysisRun", row.status, target)
        row.status = target
        now = datetime.now(timezone.utc)
        if target == AnalysisRunStatus.running and row.started_at is None:
            row.started_at = now
        if is_terminal_analysis_run(target) and row.finished_at is None:
            row.finished_at = now
        self._runs.flush()
        return row

    def set_input_payload(self, run_id: UUID, payload: dict | list | None) -> AnalysisRun:
        row = self.require(run_id)
        row.input_payload_json = payload
        self._runs.flush()
        return row

    def merge_input_payload(self, run_id: UUID, patch: dict | None) -> AnalysisRun:
        row = self.require(run_id)
        merged = merge_dict_json(
            row.input_payload_json if isinstance(row.input_payload_json, dict) else None,
            patch,
        )
        row.input_payload_json = merged
        self._runs.flush()
        return row

    def set_output_payload(self, run_id: UUID, payload: dict | list | None) -> AnalysisRun:
        row = self.require(run_id)
        row.output_payload_json = payload
        self._runs.flush()
        return row

    def merge_output_payload(self, run_id: UUID, patch: dict | None) -> AnalysisRun:
        row = self.require(run_id)
        merged = merge_dict_json(
            row.output_payload_json if isinstance(row.output_payload_json, dict) else None,
            patch,
        )
        row.output_payload_json = merged
        self._runs.flush()
        return row

    def merge_meta_json(self, run_id: UUID, patch: dict | None) -> AnalysisRun:
        row = self.require(run_id)
        merged = merge_dict_json(
            row.meta_json if isinstance(row.meta_json, dict) else None,
            patch,
        )
        row.meta_json = merged
        self._runs.flush()
        return row

    def set_error_summary(self, run_id: UUID, message: str | None) -> AnalysisRun:
        row = self.require(run_id)
        row.error_summary = message
        self._runs.flush()
        return row
