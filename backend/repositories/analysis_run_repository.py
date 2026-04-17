"""Persistence for :class:`~backend.models.analysis_run.AnalysisRun` (no business rules)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.models.project import Project

_COMPACTION_ELIGIBLE_STATUSES: tuple[AnalysisRunStatus, ...] = (
    AnalysisRunStatus.success,
    AnalysisRunStatus.partial_success,
    AnalysisRunStatus.no_data,
    AnalysisRunStatus.error,
    AnalysisRunStatus.cancelled,
)


class AnalysisRunRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def get(self, run_id: UUID) -> AnalysisRun | None:
        return self._session.get(AnalysisRun, run_id)

    def get_by_correlation_id(self, correlation_id: str) -> AnalysisRun | None:
        return self._session.scalar(
            select(AnalysisRun).where(AnalysisRun.correlation_id == correlation_id)
        )

    def list_for_project(self, project_id: UUID) -> list[AnalysisRun]:
        return list(
            self._session.scalars(
                select(AnalysisRun)
                .where(AnalysisRun.project_id == project_id)
                .order_by(AnalysisRun.created_at.desc())
            ).all()
        )

    def list_for_projects_owned_by(self, owner_user_id: UUID) -> list[AnalysisRun]:
        """All analysis runs in projects owned by ``owner_user_id`` (newest first)."""
        return list(
            self._session.scalars(
                select(AnalysisRun)
                .join(Project, AnalysisRun.project_id == Project.id)
                .where(Project.owner_user_id == owner_user_id)
                .order_by(AnalysisRun.created_at.desc())
            ).all()
        )

    def list_compaction_candidates(
        self,
        *,
        finished_before: datetime,
        limit: int,
    ) -> list[AnalysisRun]:
        payload_present = or_(
            AnalysisRun.input_payload_json.is_not(None),
            AnalysisRun.output_payload_json.is_not(None),
        )
        return list(
            self._session.scalars(
                select(AnalysisRun)
                .where(AnalysisRun.status.in_(_COMPACTION_ELIGIBLE_STATUSES))
                .where(AnalysisRun.finished_at.is_not(None))
                .where(AnalysisRun.finished_at < finished_before)
                .where(AnalysisRun.compacted_at.is_(None))
                .where(payload_present)
                .order_by(AnalysisRun.finished_at.asc(), AnalysisRun.id.asc())
                .limit(limit)
            ).all()
        )

    def add(self, row: AnalysisRun) -> AnalysisRun:
        self._session.add(row)
        return row
