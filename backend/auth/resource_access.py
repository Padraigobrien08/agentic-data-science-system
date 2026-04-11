"""Owner-scoped access checks (project → run → artifact)."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.evaluation_run import EvaluationRun
from backend.models.project import Project
from backend.models.run_step import RunStep


def get_owned_project(db: Session, project_id: UUID, user_id: UUID) -> Project | None:
    row = db.get(Project, project_id)
    if row is None or row.owner_user_id != user_id:
        return None
    return row


def get_run_for_owner(db: Session, run_id: UUID, user_id: UUID) -> AnalysisRun | None:
    run = db.get(AnalysisRun, run_id)
    if run is None:
        return None
    proj = db.get(Project, run.project_id)
    if proj is None or proj.owner_user_id != user_id:
        return None
    return run


def user_can_access_artifact(db: Session, art: Artifact, user_id: UUID) -> bool:
    run_id: UUID | None = art.analysis_run_id
    if run_id is None and art.run_step_id is not None:
        step = db.get(RunStep, art.run_step_id)
        if step is not None:
            run_id = step.analysis_run_id
    if run_id is not None:
        return get_run_for_owner(db, run_id, user_id) is not None
    if art.evaluation_run_id is not None:
        er = db.get(EvaluationRun, art.evaluation_run_id)
        if er is None or er.project_id is None:
            return False
        proj = db.get(Project, er.project_id)
        return proj is not None and proj.owner_user_id == user_id
    return False
