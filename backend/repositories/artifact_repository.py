"""Persistence for :class:`~backend.models.artifact.Artifact` rows (blobs are external)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.artifact import Artifact
from backend.models.enums import ArtifactKind


class ArtifactRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def flush(self) -> None:
        self._session.flush()

    def get(self, artifact_id: UUID) -> Artifact | None:
        return self._session.get(Artifact, artifact_id)

    def list_for_analysis_run(self, analysis_run_id: UUID) -> list[Artifact]:
        return list(
            self._session.scalars(
                select(Artifact)
                .where(Artifact.analysis_run_id == analysis_run_id)
                .order_by(Artifact.created_at, Artifact.role_key)
            ).all()
        )

    def list_for_analysis_run_window(
        self,
        analysis_run_id: UUID,
        *,
        role_key: str | None = None,
        kind: ArtifactKind | None = None,
        include_deleted: bool = True,
        limit: int | None = None,
        offset: int = 0,
    ) -> list[Artifact]:
        rows = self.list_for_analysis_run(analysis_run_id)
        if role_key is not None:
            rows = [row for row in rows if row.role_key == role_key]
        if kind is not None:
            rows = [row for row in rows if row.kind == kind]
        if not include_deleted:
            rows = [row for row in rows if row.blob_deleted_at is None]
        if offset > 0:
            rows = rows[offset:]
        if limit is not None:
            rows = rows[:limit]
        return rows

    def list_for_run_step(self, run_step_id: UUID) -> list[Artifact]:
        return list(
            self._session.scalars(
                select(Artifact)
                .where(Artifact.run_step_id == run_step_id)
                .order_by(Artifact.created_at, Artifact.role_key)
            ).all()
        )

    def list_for_evaluation_run(self, evaluation_run_id: UUID) -> list[Artifact]:
        return list(
            self._session.scalars(
                select(Artifact)
                .where(Artifact.evaluation_run_id == evaluation_run_id)
                .order_by(Artifact.created_at, Artifact.role_key)
            ).all()
        )

    def list_blob_prune_candidates(
        self,
        *,
        created_before: datetime,
        limit: int,
    ) -> list[Artifact]:
        return list(
            self._session.scalars(
                select(Artifact)
                .where(Artifact.created_at < created_before)
                .where(Artifact.blob_deleted_at.is_(None))
                .order_by(Artifact.created_at.asc(), Artifact.id.asc())
                .limit(limit)
            ).all()
        )

    def add(self, row: Artifact) -> Artifact:
        self._session.add(row)
        return row

    def delete(self, row: Artifact) -> None:
        self._session.delete(row)
