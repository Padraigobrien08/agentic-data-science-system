"""Projects: list and create for the authenticated owner."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter

from backend.api.access_checks import require_project_owned
from backend.api.auth_deps import CurrentUserDep
from backend.api.deps import DbSession
from backend.models.project import Project
from backend.schemas.project import ProjectCreate, ProjectRead
from sqlalchemy import select

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectRead])
def list_projects(db: DbSession, user: CurrentUserDep) -> list[Project]:
    stmt = (
        select(Project)
        .where(Project.owner_user_id == user.id)
        .order_by(Project.created_at.desc())
    )
    return list(db.scalars(stmt).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(project_id: UUID, db: DbSession, user: CurrentUserDep) -> Project:
    """Return one project if and only if you own it."""
    return require_project_owned(db, project_id, user.id)


@router.post("", response_model=ProjectRead, status_code=201)
def create_project(
    body: ProjectCreate,
    db: DbSession,
    user: CurrentUserDep,
) -> Project:
    tickers = [t.strip().upper() for t in (body.tickers or []) if t and t.strip()]
    row = Project(
        owner_user_id=user.id,
        name=body.name,
        slug=body.slug,
        description=body.description,
        settings_json=body.settings_json,
        tickers=tickers,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
