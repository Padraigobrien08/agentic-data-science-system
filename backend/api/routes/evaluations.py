"""Supported evaluation control-plane routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, select

from backend.api.access_checks import require_evaluation_run_owned, require_project_owned
from backend.api.auth_deps import CurrentUserDep
from backend.api.deps import DbSession
from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun
from backend.models.enums import EvaluationRunStatus
from backend.schemas.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunRead,
    SupportedEvaluationSuiteRead,
    evaluation_run_to_read,
)
from edgar_project.evaluation.catalog import (
    get_supported_evaluation_suite,
    list_supported_evaluation_suites,
)
from edgar_project.repo_layout import REPO_ROOT

router = APIRouter(prefix="/evaluations", tags=["evaluations"])


def _case_count(db: DbSession, evaluation_run_id: UUID) -> int:
    return int(
        db.scalar(
            select(func.count(EvaluationCaseResult.id)).where(
                EvaluationCaseResult.evaluation_run_id == evaluation_run_id
            )
        )
        or 0
    )


@router.get("/suites", response_model=list[SupportedEvaluationSuiteRead])
def list_evaluation_suites(_user: CurrentUserDep) -> list[SupportedEvaluationSuiteRead]:
    return [
        SupportedEvaluationSuiteRead(
            suite_id=suite.suite_id,
            label=suite.label,
            primary_mode=suite.primary_mode,
            description=suite.description,
        )
        for suite in list_supported_evaluation_suites()
    ]


@router.get("", response_model=list[EvaluationRunRead])
def list_evaluations(
    db: DbSession,
    user: CurrentUserDep,
    project_id: UUID = Query(..., description="Project to list evaluation runs for."),
) -> list[EvaluationRunRead]:
    require_project_owned(db, project_id, user.id)
    rows = list(
        db.scalars(
            select(EvaluationRun)
            .where(EvaluationRun.project_id == project_id)
            .order_by(EvaluationRun.created_at.desc())
        ).all()
    )
    return [evaluation_run_to_read(row, case_count=_case_count(db, row.id)) for row in rows]


@router.post("", response_model=EvaluationRunRead, status_code=201)
def create_evaluation_run(
    body: EvaluationRunCreate,
    db: DbSession,
    user: CurrentUserDep,
) -> EvaluationRunRead:
    require_project_owned(db, body.project_id, user.id)
    try:
        suite = get_supported_evaluation_suite(body.suite_id)
    except KeyError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    manifest_rel = str(suite.manifest_path.relative_to(REPO_ROOT))
    row = EvaluationRun(
        project_id=body.project_id,
        initiated_by_user_id=user.id,
        suite_id=suite.suite_id,
        suite_manifest_path=manifest_rel,
        status=EvaluationRunStatus.pending,
        config_json=body.config_json,
        notes=body.notes,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return evaluation_run_to_read(row, case_count=0)


@router.get("/{evaluation_run_id}", response_model=EvaluationRunRead)
def get_evaluation_run(
    evaluation_run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> EvaluationRunRead:
    row = require_evaluation_run_owned(db, evaluation_run_id, user.id)
    return evaluation_run_to_read(row, case_count=_case_count(db, row.id))
