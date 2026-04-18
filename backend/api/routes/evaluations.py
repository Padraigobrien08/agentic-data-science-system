"""Supported evaluation control-plane routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, HTTPException, Query
from sqlalchemy import func, select

from backend.api.access_checks import require_evaluation_run_owned, require_project_owned
from backend.api.auth_deps import CurrentUserDep
from backend.api.deps import DbSession, EvaluationControlPlaneServiceDep
from backend.models.evaluation_case_result import EvaluationCaseResult
from backend.models.evaluation_run import EvaluationRun
from backend.models.enums import EvaluationRunStatus
from backend.schemas.evaluation_case_result import (
    EvaluationCaseResultRead,
    evaluation_case_result_to_read,
)
from backend.schemas.evaluation_run import (
    EvaluationRunCreate,
    EvaluationRunRead,
    EvaluationRunStartRequest,
    SupportedEvaluationSuiteRead,
    evaluation_run_to_read,
)
from edgar_project.evaluation.catalog import (
    get_supported_evaluation_suite,
    list_supported_evaluation_suites,
)
from edgar_project.evaluation.schemas import (
    EvaluationStatus,
    InputMode,
    ValidationDegradationClass,
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
    service: EvaluationControlPlaneServiceDep,
) -> EvaluationRunRead:
    require_evaluation_run_owned(db, evaluation_run_id, user.id)
    row = service.refresh_linked_case_results(evaluation_run_id)
    return evaluation_run_to_read(row, case_count=_case_count(db, row.id))


@router.get(
    "/{evaluation_run_id}/cases",
    response_model=list[EvaluationCaseResultRead],
)
def list_evaluation_case_results(
    evaluation_run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    service: EvaluationControlPlaneServiceDep,
    status: EvaluationStatus | None = Query(default=None),
    input_mode: InputMode | None = Query(default=None),
    degradation_class: ValidationDegradationClass | None = Query(default=None),
) -> list[EvaluationCaseResultRead]:
    require_evaluation_run_owned(db, evaluation_run_id, user.id)
    service.refresh_linked_case_results(evaluation_run_id)
    stmt = (
        select(EvaluationCaseResult)
        .where(EvaluationCaseResult.evaluation_run_id == evaluation_run_id)
        .order_by(EvaluationCaseResult.case_id.asc())
    )
    if status is not None:
        stmt = stmt.where(EvaluationCaseResult.status == status.value)
    if input_mode is not None:
        stmt = stmt.where(EvaluationCaseResult.input_mode == input_mode.value)
    if degradation_class is not None:
        stmt = stmt.where(
            EvaluationCaseResult.degradation_class == degradation_class.value
        )
    rows = list(db.scalars(stmt).all())
    return [evaluation_case_result_to_read(row) for row in rows]


@router.get(
    "/{evaluation_run_id}/cases/{case_id}",
    response_model=EvaluationCaseResultRead,
)
def get_evaluation_case_result(
    evaluation_run_id: UUID,
    case_id: str,
    db: DbSession,
    user: CurrentUserDep,
    service: EvaluationControlPlaneServiceDep,
) -> EvaluationCaseResultRead:
    require_evaluation_run_owned(db, evaluation_run_id, user.id)
    service.refresh_linked_case_results(evaluation_run_id)
    row = db.scalar(
        select(EvaluationCaseResult).where(
            EvaluationCaseResult.evaluation_run_id == evaluation_run_id,
            EvaluationCaseResult.case_id == case_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Evaluation case result not found.")
    return evaluation_case_result_to_read(row)


@router.post("/{evaluation_run_id}/start", response_model=EvaluationRunRead)
def start_evaluation_run(
    evaluation_run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    service: EvaluationControlPlaneServiceDep,
    body: EvaluationRunStartRequest = Body(default_factory=EvaluationRunStartRequest),
) -> EvaluationRunRead:
    row = require_evaluation_run_owned(db, evaluation_run_id, user.id)
    if row.status != EvaluationRunStatus.pending:
        raise HTTPException(status_code=409, detail="Evaluation run is not pending.")

    updated = service.start_evaluation_run(
        evaluation_run_id,
        allow_live=body.allow_live,
    )
    db.commit()
    db.refresh(updated)
    return evaluation_run_to_read(
        updated,
        case_count=service.count_case_results(updated.id),
    )
