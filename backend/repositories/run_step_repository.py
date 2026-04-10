"""Persistence for :class:`~backend.models.run_step.RunStep`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.run_step import RunStep


class RunStepRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def get(self, step_id: UUID) -> RunStep | None:
        return self._session.get(RunStep, step_id)

    def get_by_run_and_index(self, analysis_run_id: UUID, step_index: int) -> RunStep | None:
        return self._session.scalar(
            select(RunStep).where(
                RunStep.analysis_run_id == analysis_run_id,
                RunStep.step_index == step_index,
            )
        )

    def list_for_analysis_run(self, analysis_run_id: UUID) -> list[RunStep]:
        return list(
            self._session.scalars(
                select(RunStep)
                .where(RunStep.analysis_run_id == analysis_run_id)
                .order_by(RunStep.step_index)
            ).all()
        )

    def add(self, row: RunStep) -> RunStep:
        self._session.add(row)
        return row
