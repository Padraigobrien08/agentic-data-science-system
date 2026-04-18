"""Persistence helpers for :class:`~backend.models.evaluation_run.EvaluationRun`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun


class EvaluationRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, row: EvaluationRun) -> EvaluationRun:
        self._session.add(row)
        return row

    def flush(self) -> None:
        self._session.flush()

    def get(self, evaluation_run_id: UUID) -> EvaluationRun | None:
        return self._session.get(EvaluationRun, evaluation_run_id)

    def get_for_update(self, evaluation_run_id: UUID) -> EvaluationRun | None:
        stmt = (
            select(EvaluationRun)
            .where(EvaluationRun.id == evaluation_run_id)
            .with_for_update()
        )
        return self._session.scalar(stmt)

    def list_for_project(self, project_id: UUID) -> list[EvaluationRun]:
        return list(
            self._session.scalars(
                select(EvaluationRun)
                .where(EvaluationRun.project_id == project_id)
                .order_by(EvaluationRun.created_at.desc())
            ).all()
        )

    def count_case_results(self, evaluation_run_id: UUID) -> int:
        return int(
            self._session.scalar(
                select(func.count(EvaluationCaseResult.id)).where(
                    EvaluationCaseResult.evaluation_run_id == evaluation_run_id
                )
            )
            or 0
        )
