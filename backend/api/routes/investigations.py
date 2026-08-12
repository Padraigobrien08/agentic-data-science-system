"""Read-only API for the generalized investigation model (owner-scoped)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request

from agentic.agent.replay import ReplayNotPossible
from backend.api.access_checks import require_investigation_owned, require_project_owned
from backend.api.auth_deps import CurrentUserDep, require_admin_debug_access
from backend.api.deps import DbSession
from backend.api.routes.runs import guard_run_admission
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.schemas.investigation import (
    InvestigationCreateRequest,
    InvestigationCreateResponse,
    InvestigationDetail,
    InvestigationSummary,
    build_detail,
    build_summary,
)
from backend.schemas.replay import ReplayResponse, build_replay_response
from backend.services.investigation_create_service import (
    AgenticEngineDisabledError,
    InvalidDatasetError,
    InvestigationCreateService,
)
from backend.services.investigation_replay_service import InvestigationReplayService
from backend.services.spend_guard import ENGINE_AGENTIC

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationCreateResponse, status_code=201)
def create_investigation(
    body: InvestigationCreateRequest,
    request: Request,
    db: DbSession,
    user: CurrentUserDep,
) -> InvestigationCreateResponse:
    """Create an agentic investigation over a dataset and run it.

    ``dataset.source`` selects the adapter: ``tabular`` (pasted CSV or inline records, the
    default) or ``edgar`` (SEC filings for ``dataset.entities``). Both run the same loop over
    the same evidence model — EDGAR is an adapter, not a separate product.

    Synchronous by default; ``async_execution=true`` enqueues it for the worker. Prefer async
    for ``edgar``: the panel is built from live SEC fetches before the loop starts, which is
    far too slow to hold an HTTP request open for.

    Requires the agentic engine flag; owner-scoped to the target project.
    """
    require_project_owned(db, body.project_id, user.id)
    # This route always drives the agentic engine, so the entitlement is checked explicitly
    # rather than inferred from an ``engine`` field in a payload.
    guard_run_admission(db, user, requested_engine=ENGINE_AGENTIC)
    service = InvestigationCreateService(db)
    kwargs = dict(
        project_id=body.project_id,
        user_id=user.id,
        goal=body.goal,
        dataset_format=body.dataset.format,
        csv_text=body.dataset.csv_text,
        records=body.dataset.records,
        name=body.dataset.name,
        time_field=body.dataset.time_field,
        entity_id_fields=body.dataset.entity_id_fields,
        source=body.dataset.source,
        entities=body.dataset.entities,
        refresh=body.dataset.refresh,
    )
    try:
        if body.async_execution:
            tc = getattr(request.state, "trace_carrier_for_jobs", None)
            result = service.create_and_enqueue(**kwargs, trace_carrier=tc)
        else:
            result = service.create_and_run(**kwargs)
    except AgenticEngineDisabledError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidDatasetError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return InvestigationCreateResponse(
        analysis_run_id=result.analysis_run_id,
        status=result.status,
        db_status=result.db_status,
        investigation_id=result.investigation_id,
        queued=result.queued,
    )


@router.get("", response_model=list[InvestigationSummary])
def list_investigations(
    db: DbSession,
    user: CurrentUserDep,
    project_id: UUID | None = Query(default=None, description="Scope to one owned project"),
    analysis_run_id: UUID | None = Query(default=None, description="Resolve the investigation for a run"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[InvestigationSummary]:
    """List investigations owned by the user's projects (or initiated by the user), newest first."""
    if project_id is not None:
        require_project_owned(db, project_id, user.id)
    repo = SqlAlchemyInvestigationRepository(db)
    rows = repo.list_for_user(
        user.id, project_id=project_id, analysis_run_id=analysis_run_id, limit=limit, offset=offset
    )
    return [build_summary(row) for row in rows]


@router.post("/{investigation_id}/replay", response_model=ReplayResponse)
def replay_investigation_route(
    investigation_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> ReplayResponse:
    """
    Re-run this investigation under the currently configured policy and diff the outcome.

    Answers "did changing the model / prompt / budget change our answers, or only the route to
    them?" against a real persisted run. The verdict is conclusion-first: ``identical``,
    ``same_conclusion``, or ``diverged``.

    **Admin only, and deliberately so.** A replay is a full investigation and costs real model
    spend, but the candidate is never persisted — that is a design decision in
    :mod:`agentic.agent.replay`, since sharing a store with the baseline would overwrite the
    run being compared against. The consequence is that a replay produces no ``AnalysisRun``
    and no ``ModelCall`` rows, so :mod:`backend.services.spend_guard` cannot see or count it.
    An endpoint that spends money invisibly to the ceilings must not be reachable by ordinary
    accounts.

    **Synchronous**, and as slow as the investigation it replays — tens of seconds against a
    real model. There is no background variant: the candidate is not persisted, so there would
    be nothing for a worker to hand back.

    Refuses with **409** when the baseline's dataset can no longer be reconstructed. Replay
    reuses the exact panel the baseline ran on; re-fetching would change the data underneath
    the comparison and attribute to the policy a difference that came from the data.
    """
    row = require_investigation_owned(db, investigation_id, user.id)
    require_admin_debug_access(user, feature="investigation replay")

    if row.analysis_run_id is None:
        raise HTTPException(
            status_code=409,
            detail="This investigation has no analysis run to replay.",
        )
    try:
        result = InvestigationReplayService(db).replay_run(row.analysis_run_id)
    except ReplayNotPossible as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    return build_replay_response(
        result,
        investigation_id=str(investigation_id),
        analysis_run_id=str(row.analysis_run_id),
    )


@router.get("/{investigation_id}", response_model=InvestigationDetail)
def get_investigation(
    investigation_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> InvestigationDetail:
    """Full investigation: hypotheses, evidence, agent decisions, critiques, experiments, conclusion, timeline."""
    row = require_investigation_owned(db, investigation_id, user.id)
    return build_detail(row)
