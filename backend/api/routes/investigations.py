"""Read-only API for the generalized investigation model (owner-scoped)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from backend.api.access_checks import require_investigation_owned, require_project_owned
from backend.api.auth_deps import CurrentUserDep
from backend.api.deps import DbSession
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationCreateResponse,
    InvestigationDetail,
    InvestigationSummary,
    build_detail,
    build_summary,
)
from backend.services.investigation_create_service import (
    AgenticEngineDisabledError,
    InvalidDatasetError,
    InvestigationCreateService,
)

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationCreateResponse, status_code=201)
def create_investigation(
    body: InvestigationCreateRequest,
    db: DbSession,
    user: CurrentUserDep,
) -> InvestigationCreateResponse:
    """Create an agentic investigation over a user-provided dataset and run it (synchronous).

    Requires the agentic engine flag to be enabled; owner-scoped to the target project.
    """
    require_project_owned(db, body.project_id, user.id)
    try:
        result = InvestigationCreateService(db).create_and_run(
            project_id=body.project_id,
            user_id=user.id,
            goal=body.goal,
            dataset_format=body.dataset.format,
            csv_text=body.dataset.csv_text,
            records=body.dataset.records,
            name=body.dataset.name,
            time_field=body.dataset.time_field,
            entity_id_fields=body.dataset.entity_id_fields,
        )
    except AgenticEngineDisabledError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidDatasetError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InvestigationCreateResponse(
        investigation_id=result.investigation_id,
        analysis_run_id=result.analysis_run_id,
        status=result.status,
        db_status=result.db_status,
    )


@router.get("", response_model=list[InvestigationSummary])
def list_investigations(
    db: DbSession,
    user: CurrentUserDep,
    project_id: UUID | None = Query(default=None, description="Scope to one owned project"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[InvestigationSummary]:
    """List investigations owned by the user's projects (or initiated by the user), newest first."""
    if project_id is not None:
        require_project_owned(db, project_id, user.id)
    repo = SqlAlchemyInvestigationRepository(db)
    rows = repo.list_for_user(user.id, project_id=project_id, limit=limit, offset=offset)
    return [build_summary(row) for row in rows]


@router.get("/{investigation_id}", response_model=InvestigationDetail)
def get_investigation(
    investigation_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> InvestigationDetail:
    """Full investigation: hypotheses, evidence, agent decisions, critiques, experiments, conclusion, timeline."""
    row = require_investigation_owned(db, investigation_id, user.id)
    return build_detail(row)
