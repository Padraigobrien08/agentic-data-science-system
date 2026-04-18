"""Persistence helpers for :class:`~backend.models.evaluation_case_result.EvaluationCaseResult`."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from backend.models.evaluation_case_result import EvaluationCaseResult


class EvaluationCaseResultRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def list_for_run(self, evaluation_run_id: UUID) -> list[EvaluationCaseResult]:
        return list(
            self._session.scalars(
                select(EvaluationCaseResult)
                .where(EvaluationCaseResult.evaluation_run_id == evaluation_run_id)
                .order_by(EvaluationCaseResult.case_id.asc())
            ).all()
        )

    def count_for_run(self, evaluation_run_id: UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count(EvaluationCaseResult.id)).where(
                    EvaluationCaseResult.evaluation_run_id == evaluation_run_id
                )
            )
            or 0
        )

    def get_for_run_case(
        self,
        evaluation_run_id: UUID,
        case_id: str,
    ) -> EvaluationCaseResult | None:
        return self._session.scalar(
            select(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == evaluation_run_id,
                EvaluationCaseResult.case_id == case_id,
            )
        )

    def update_linked_analysis_run(
        self,
        case_row: EvaluationCaseResult,
        *,
        latest_analysis_run_id: UUID,
        latest_analysis_run_status: str,
        history_item: dict[str, object],
        max_history_entries: int = 5,
    ) -> EvaluationCaseResult:
        existing = case_row.analysis_run_history_json
        if isinstance(existing, list):
            history = [item for item in existing if isinstance(item, dict)]
        else:
            history = []
        history.append(history_item)
        case_row.latest_analysis_run_id = latest_analysis_run_id
        case_row.latest_analysis_run_status = latest_analysis_run_status
        case_row.analysis_run_history_json = history[-max_history_entries:]
        self._session.flush()
        return case_row

    def touch_updated_at(
        self,
        case_row: EvaluationCaseResult,
        *,
        updated_at: datetime | None = None,
    ) -> EvaluationCaseResult:
        case_row.updated_at = updated_at
        self._session.flush()
        return case_row

    def replace_for_run(
        self,
        evaluation_run_id: UUID,
        rows: list[EvaluationCaseResult],
    ) -> list[EvaluationCaseResult]:
        self._session.execute(
            delete(EvaluationCaseResult).where(
                EvaluationCaseResult.evaluation_run_id == evaluation_run_id
            )
        )
        if rows:
            self._session.add_all(rows)
        self._session.flush()
        return rows
