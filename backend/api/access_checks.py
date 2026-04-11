"""HTTP-facing owner checks — consistent 404 for missing or non-owned resources."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy.orm import Session

from backend.auth.resource_access import get_owned_project, get_run_for_owner, user_can_access_artifact
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.project import Project
from backend.services.artifact_service import ArtifactService


def require_project_owned(db: Session, project_id: UUID, user_id: UUID) -> Project:
    row = get_owned_project(db, project_id, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return row


def require_analysis_run_owned(db: Session, run_id: UUID, user_id: UUID) -> AnalysisRun:
    row = get_run_for_owner(db, run_id, user_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return row


def require_artifact_readable(
    db: Session,
    art_svc: ArtifactService,
    artifact_id: UUID,
    user_id: UUID,
) -> Artifact:
    row = art_svc.get(artifact_id)
    if row is None or not user_can_access_artifact(db, row, user_id):
        raise HTTPException(status_code=404, detail="Artifact not found")
    return row
