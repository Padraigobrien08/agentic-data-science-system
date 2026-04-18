"""Persistence helpers for :class:`~backend.models.evaluation_case_result.EvaluationCaseResult`."""

from __future__ import annotations

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
