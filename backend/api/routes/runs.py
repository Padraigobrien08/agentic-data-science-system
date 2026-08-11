"""Analysis run CRUD and synchronous EDGAR execution (Phase A)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from backend.api.access_checks import require_analysis_run_owned, require_project_owned
from backend.api.auth_deps import CurrentUserDep, require_admin_debug_access
from backend.api.deps import AnalysisRunServiceDep, ArtifactServiceDep, DbSession, EdgarPipelineExecutionDep
from backend.config.settings import get_settings
from backend.domain.run_progress import derive_run_progress_public
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind, ModelCallStatus, RunStepStatus
from backend.models.model_call import ModelCall
from backend.observability.tracing import attach_trace_carrier, bind_current_trace_for_logs, get_tracer
from backend.repositories.artifact_repository import ArtifactRepository
from backend.repositories.model_call_repository import ModelCallRepository
from backend.repositories.run_step_repository import RunStepRepository
from backend.schemas.analysis_run import AnalysisRunCreate
from backend.schemas.api_phase_a import (
    AnalysisRunDetailResponse,
    AnalysisRunSummary,
    ArtifactMetadata,
    ModelCallApiItem,
    RunStepDetailItem,
    RunTraceArtifactPreview,
    RunTraceModelCallPreview,
    RunTraceShellResponse,
    RunTraceStepPreview,
    analysis_run_to_detail,
    analysis_run_to_summary,
    artifact_to_metadata,
    model_call_to_api_item,
    run_step_to_detail,
)
from backend.schemas.execute_run import ExecuteRunOverrides, ExecuteRunResponse
from backend.schemas.llm_usage import (
    LlmRunUsageSummary,
    aggregate_llm_usage_for_calls,
    to_transparency_wire,
)
from backend.schemas.prompt_routing import PromptRoutingPreviewRequest, PromptRoutingPreviewResponse
from backend.schemas.run_lifecycle import (
    AnalysisRunStatusResponse,
    RunRetryRequest,
    analysis_run_status_to_response,
)
from backend.schemas.run_transparency import RunTransparencySummary, build_run_transparency_summary
from backend.services.agentic_investigation_execution_service import (
    ENGINE_AGENTIC,
    AgenticInvestigationExecutionService,
    select_run_engine,
)
from backend.services.exceptions import InvalidStatusTransition, RunCancelledDuringExecution, RunLifecycleError
from backend.services.run_lifecycle_service import RunLifecycleService
from backend.services.run_queue_service import RunQueueService
from backend.services.spend_guard import (
    EngineNotEntitled,
    SpendLimitExceeded,
    assert_engine_entitled,
    check_run_admission,
)
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import OrchestrationInput, PlanningOutcome

router = APIRouter(prefix="/runs", tags=["runs"])


def _build_run_transparency(
    *,
    db: DbSession,
    run_id: UUID,
    meta_json: dict | list | None,
    artifacts: list[Artifact],
) -> tuple[list[ModelCall], RunTransparencySummary]:
    calls_rows = ModelCallRepository(db).list_for_analysis_run(run_id)
    settings = get_settings()
    usage = aggregate_llm_usage_for_calls(
        run_id,
        list(calls_rows),
        pricing_json=settings.agent_llm_pricing_json,
    )
    trans = build_run_transparency_summary(
        meta_json,
        model_call_count=len(calls_rows),
        artifacts=artifacts,
        llm_usage=to_transparency_wire(usage),
    )
    return calls_rows, trans


def _artifact_ids_by_step(artifacts: list[Artifact]) -> dict[UUID, list[UUID]]:
    by_step: dict[UUID, list[UUID]] = {}
    for artifact in artifacts:
        if artifact.run_step_id is not None:
            by_step.setdefault(artifact.run_step_id, []).append(artifact.id)
    return by_step


def _to_prompt_routing_preview_response(outcome: PlanningOutcome) -> PromptRoutingPreviewResponse:
    interpreted_goal = outcome.interpreted_goal
    return PromptRoutingPreviewResponse(
        supported=outcome.ok,
        routing_source=outcome.routing_source,
        effective_tickers=list(outcome.effective_tickers),
        out_of_scope_tickers=list(outcome.out_of_scope_tickers),
        rewrite_suggestions=list(outcome.rewrite_suggestions),
        reason=None if outcome.ok else (outcome.errors[0].message if outcome.errors else None),
        intent=interpreted_goal.intent if interpreted_goal is not None else None,
        goal_code=interpreted_goal.code if interpreted_goal is not None else None,
        plan_template_id=(
            interpreted_goal.plan_template.template_id
            if interpreted_goal is not None and interpreted_goal.plan_template is not None
            else None
        ),
    )


@router.post("/route-preview", response_model=PromptRoutingPreviewResponse)
def route_preview(
    body: PromptRoutingPreviewRequest,
    db: DbSession,
    user: CurrentUserDep,
) -> PromptRoutingPreviewResponse:
    """Preview deterministic routing for a project-scoped prompt without creating a run."""
    require_project_owned(db, body.project_id, user.id)
    outcome = Planner().build_plan(
        OrchestrationInput(
            tickers=body.tickers,
            analysis_goal=body.analysis_goal,
            refresh=body.refresh,
        )
    )
    return _to_prompt_routing_preview_response(outcome)


def _requested_engine(payload: object) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("engine") or "").strip().lower()


def guard_run_admission(db: DbSession, user, *, requested_engine: str = "") -> None:
    """
    Refuse a run that would exceed an entitlement or a spend ceiling.

    Called before any path that puts a run into execution — create-with-enqueue, execute, and
    retry — because refusing after the work has started spends exactly the money the guard
    exists to protect. Creating a ``pending`` row is free and is deliberately not gated.
    """
    settings = get_settings()
    try:
        if requested_engine:
            assert_engine_entitled(user, requested_engine, settings=settings)
        check_run_admission(db, user, settings=settings)
    except EngineNotEntitled as exc:
        db.rollback()
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except SpendLimitExceeded as exc:
        db.rollback()
        raise HTTPException(status_code=429, detail=str(exc)) from exc


@router.post("", response_model=AnalysisRunSummary, status_code=201)
def create_run(
    body: AnalysisRunCreate,
    request: Request,
    db: DbSession,
    run_svc: AnalysisRunServiceDep,
    user: CurrentUserDep,
) -> AnalysisRunSummary:
    """Create an analysis run in ``pending`` (orchestration execution is not started here)."""
    require_project_owned(db, body.project_id, user.id)
    if body.enqueue_execution:
        guard_run_admission(db, user, requested_engine=_requested_engine(body.input_payload_json))
    try:
        row = run_svc.create(
            body.project_id,
            initiated_by_user_id=user.id,
            correlation_id=body.correlation_id,
            orchestration_goal_text=body.orchestration_goal_text,
            input_payload_json=body.input_payload_json,
            meta_json=body.meta_json,
        )
        if body.enqueue_execution:
            overrides = (
                body.enqueue_overrides.model_dump(exclude_none=True) if body.enqueue_overrides else None
            )
            tc = getattr(request.state, "trace_carrier_for_jobs", None)
            RunQueueService(db).enqueue_after_create(row.id, overrides, trace_carrier=tc)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail="Unique constraint violation (e.g. correlation_id already exists)",
        ) from None
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.refresh(row)
    return analysis_run_to_summary(row)


@router.get("", response_model=list[AnalysisRunSummary])
def list_runs(
    db: DbSession,
    run_svc: AnalysisRunServiceDep,
    user: CurrentUserDep,
    project_id: UUID | None = Query(
        None,
        description="If set, list runs for this project (must be yours). If omitted, list runs across all projects you own.",
    ),
) -> list[AnalysisRunSummary]:
    """List runs (newest first), scoped to the current user."""
    if project_id is not None:
        require_project_owned(db, project_id, user.id)
        rows = run_svc.list_for_project(project_id)
    else:
        rows = run_svc.list_for_projects_owned_by(user.id)
    step_repo = RunStepRepository(db)
    grouped = step_repo.list_grouped_by_run_ids([r.id for r in rows])
    return [
        analysis_run_to_summary(
            r,
            progress=derive_run_progress_public(r.status, grouped.get(r.id, [])),
        )
        for r in rows
    ]


@router.get("/{run_id}/status", response_model=AnalysisRunStatusResponse)
def get_run_status(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> AnalysisRunStatusResponse:
    """Execution-focused status: terminal flag, open job, latest job, and attempt history."""
    require_analysis_run_owned(db, run_id, user.id)
    try:
        row, has_open, latest, history = RunLifecycleService(db).build_status_view(run_id)
    except RunLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return analysis_run_status_to_response(
        row,
        has_open_execution_job=has_open,
        latest_execution_job=latest,
        execution_job_history=history,
    )


@router.post("/{run_id}/cancel", response_model=AnalysisRunSummary)
def cancel_run(run_id: UUID, db: DbSession, user: CurrentUserDep) -> AnalysisRunSummary:
    """Cancel a non-terminal run (``pending``, ``queued``, or ``running``)."""
    require_analysis_run_owned(db, run_id, user.id)
    try:
        row = RunLifecycleService(db).cancel_analysis_run(run_id)
        db.commit()
    except RunLifecycleError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except InvalidStatusTransition as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(row)
    return analysis_run_to_summary(row)


@router.post("/{run_id}/retry", response_model=AnalysisRunSummary)
def retry_run(
    run_id: UUID,
    request: Request,
    db: DbSession,
    user: CurrentUserDep,
    body: RunRetryRequest | None = None,
) -> AnalysisRunSummary:
    """Re-queue a finished non-success run for background execution."""
    row_for_guard = require_analysis_run_owned(db, run_id, user.id)
    guard_run_admission(db, user, requested_engine=_requested_engine(row_for_guard.input_payload_json))
    overrides = (
        body.enqueue_overrides.model_dump(exclude_none=True)
        if body is not None and body.enqueue_overrides is not None
        else None
    )
    try:
        tc = getattr(request.state, "trace_carrier_for_jobs", None)
        row = RunLifecycleService(db).retry_analysis_run(
            run_id, overrides=overrides, trace_carrier=tc
        )
        db.commit()
    except RunLifecycleError as exc:
        db.rollback()
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except InvalidStatusTransition as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    db.refresh(row)
    return analysis_run_to_summary(row)


@router.get("/{run_id}", response_model=AnalysisRunDetailResponse)
def get_run(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    art_svc: ArtifactServiceDep,
    include_payloads: bool = Query(
        False,
        description="When true, include input_payload_json, output_payload_json, and meta_json",
    ),
    include_transparency: bool = Query(
        False,
        description="When true, include typed ``transparency`` (evidence artifact ids, prompt_versions, model_call_count).",
    ),
) -> AnalysisRunDetailResponse:
    row = require_analysis_run_owned(db, run_id, user.id)
    if include_payloads:
        require_admin_debug_access(user, feature="raw run payloads")
    steps = RunStepRepository(db).list_for_analysis_run(run_id)
    progress = derive_run_progress_public(row.status, steps)
    trans = None
    if include_transparency:
        arts = art_svc.list_for_analysis_run(run_id)
        _, trans = _build_run_transparency(
            db=db,
            run_id=run_id,
            meta_json=row.meta_json,
            artifacts=arts,
        )
    return analysis_run_to_detail(
        row,
        include_payloads=include_payloads,
        transparency=trans,
        progress=progress,
    )


@router.get("/{run_id}/trace-summary", response_model=RunTraceShellResponse)
def get_run_trace_summary(
    run_id: UUID,
    db: DbSession,
    art_svc: ArtifactServiceDep,
    user: CurrentUserDep,
    steps_limit: int = Query(5, ge=1, le=25),
    artifacts_limit: int = Query(5, ge=1, le=25),
    model_calls_limit: int = Query(5, ge=1, le=25),
) -> RunTraceShellResponse:
    row = require_analysis_run_owned(db, run_id, user.id)
    step_repo = RunStepRepository(db)
    artifact_repo = ArtifactRepository(db)
    model_call_repo = ModelCallRepository(db)

    all_steps = step_repo.list_for_analysis_run(run_id)
    progress = derive_run_progress_public(row.status, all_steps)
    all_artifacts = art_svc.list_for_analysis_run(run_id)
    all_model_calls, transparency = _build_run_transparency(
        db=db,
        run_id=run_id,
        meta_json=row.meta_json,
        artifacts=all_artifacts,
    )
    linked_artifacts = _artifact_ids_by_step(all_artifacts)

    preview_steps = step_repo.list_for_analysis_run_window(run_id, limit=steps_limit)
    preview_artifacts = artifact_repo.list_for_analysis_run_window(run_id, limit=artifacts_limit)
    preview_model_calls = model_call_repo.list_for_analysis_run(run_id, limit=model_calls_limit)
    timeline_preview = [
        run_step_to_detail(
            step,
            include_payloads=False,
            include_transparency=True,
            linked_artifact_ids=linked_artifacts.get(step.id),
        )
        for step in preview_steps
    ]

    return RunTraceShellResponse(
        run=analysis_run_to_summary(row, progress=progress),
        transparency=transparency,
        timeline_preview=timeline_preview,
        steps=RunTraceStepPreview(
            total=len(all_steps),
            limit=steps_limit,
            has_more=len(all_steps) > steps_limit,
            items=timeline_preview,
        ),
        artifacts=RunTraceArtifactPreview(
            total=len(all_artifacts),
            limit=artifacts_limit,
            has_more=len(all_artifacts) > artifacts_limit,
            items=[artifact_to_metadata(artifact) for artifact in preview_artifacts],
        ),
        model_calls=RunTraceModelCallPreview(
            total=len(all_model_calls),
            limit=model_calls_limit,
            has_more=len(all_model_calls) > model_calls_limit,
            items=[
                model_call_to_api_item(model_call, include_payloads=False)
                for model_call in preview_model_calls
            ],
        ),
    )


@router.get("/{run_id}/steps", response_model=list[RunStepDetailItem])
def list_run_steps(
    run_id: UUID,
    db: DbSession,
    art_svc: ArtifactServiceDep,
    user: CurrentUserDep,
    include_payloads: bool = Query(
        False,
        description="When true, include planner_tool_input_json and meta_json per step",
    ),
    include_transparency: bool = Query(
        False,
        description="When true, include per-step ``transparency`` (trace lane, model_call_id, output_summary, linked_artifact_ids).",
    ),
    status: RunStepStatus | None = Query(None),
    trace: str | None = Query(None),
    q: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[RunStepDetailItem]:
    require_analysis_run_owned(db, run_id, user.id)
    if include_payloads:
        require_admin_debug_access(user, feature="raw run step payloads")
    step_repo = RunStepRepository(db)
    steps = step_repo.list_for_analysis_run_window(
        run_id,
        status=status,
        trace=trace,
        q=q,
        limit=limit,
        offset=offset,
    )
    art_by_step: dict[UUID, list[UUID]] = {}
    if include_transparency:
        art_by_step = _artifact_ids_by_step(art_svc.list_for_analysis_run(run_id))
    return [
        run_step_to_detail(
            s,
            include_payloads=include_payloads,
            include_transparency=include_transparency,
            linked_artifact_ids=art_by_step.get(s.id),
        )
        for s in steps
    ]


@router.get("/{run_id}/steps/{step_id}", response_model=RunStepDetailItem)
def get_run_step(
    run_id: UUID,
    step_id: UUID,
    db: DbSession,
    art_svc: ArtifactServiceDep,
    user: CurrentUserDep,
    include_payloads: bool = Query(
        False,
        description="When true, include planner_tool_input_json and meta_json for this step.",
    ),
    include_transparency: bool = Query(
        False,
        description="When true, include per-step ``transparency`` for this step.",
    ),
) -> RunStepDetailItem:
    require_analysis_run_owned(db, run_id, user.id)
    if include_payloads:
        require_admin_debug_access(user, feature="raw run step payloads")
    row = RunStepRepository(db).get(step_id)
    if row is None or row.analysis_run_id != run_id:
        raise HTTPException(status_code=404, detail="Run step not found")
    art_by_step = _artifact_ids_by_step(art_svc.list_for_analysis_run(run_id)) if include_transparency else {}
    return run_step_to_detail(
        row,
        include_payloads=include_payloads,
        include_transparency=include_transparency,
        linked_artifact_ids=art_by_step.get(row.id),
    )


@router.get("/{run_id}/artifacts", response_model=list[ArtifactMetadata])
def list_run_artifacts(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    role_key: str | None = Query(None),
    kind: ArtifactKind | None = Query(None),
    include_deleted: bool = Query(True),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ArtifactMetadata]:
    require_analysis_run_owned(db, run_id, user.id)
    rows = ArtifactRepository(db).list_for_analysis_run_window(
        run_id,
        role_key=role_key,
        kind=kind,
        include_deleted=include_deleted,
        limit=limit,
        offset=offset,
    )
    return [artifact_to_metadata(a) for a in rows]


@router.get("/{run_id}/model-calls", response_model=list[ModelCallApiItem])
def list_run_model_calls(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    include_payloads: bool = Query(
        False,
        description="When true, include request_payload_json and response_payload_json (can be large).",
    ),
    status: ModelCallStatus | None = Query(None),
    prompt_id: str | None = Query(None),
    q: str | None = Query(None),
    limit: int | None = Query(None, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[ModelCallApiItem]:
    """List ModelCall rows for this analysis run (audit: model, prompt version, tokens, latency)."""
    require_analysis_run_owned(db, run_id, user.id)
    if include_payloads:
        require_admin_debug_access(user, feature="raw model call payloads")
    rows = ModelCallRepository(db).list_for_analysis_run(
        run_id,
        status=status,
        prompt_id=prompt_id,
        q=q,
        limit=limit,
        offset=offset,
    )
    return [model_call_to_api_item(r, include_payloads=include_payloads) for r in rows]


@router.get("/{run_id}/model-calls/{model_call_id}", response_model=ModelCallApiItem)
def get_run_model_call(
    run_id: UUID,
    model_call_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    include_payloads: bool = Query(
        False,
        description="When true, include request_payload_json and response_payload_json for this model call.",
    ),
) -> ModelCallApiItem:
    require_analysis_run_owned(db, run_id, user.id)
    if include_payloads:
        require_admin_debug_access(user, feature="raw model call payloads")
    row = ModelCallRepository(db).get(model_call_id)
    if row is None or row.analysis_run_id != run_id:
        raise HTTPException(status_code=404, detail="Model call not found")
    return model_call_to_api_item(row, include_payloads=include_payloads)


@router.get("/{run_id}/llm-usage", response_model=LlmRunUsageSummary)
def get_run_llm_usage(
    run_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
) -> LlmRunUsageSummary:
    """Aggregate prompt/completion tokens, latency, and optional USD estimates by agent phase."""
    require_analysis_run_owned(db, run_id, user.id)
    settings = get_settings()
    rows = db.scalars(
        select(ModelCall)
        .where(ModelCall.analysis_run_id == run_id)
        .order_by(ModelCall.created_at.asc())
    ).all()
    return aggregate_llm_usage_for_calls(
        run_id,
        list(rows),
        pricing_json=settings.agent_llm_pricing_json,
    )


@router.post("/{run_id}/execute", response_model=ExecuteRunResponse)
def execute_run(
    run_id: UUID,
    request: Request,
    db: DbSession,
    pipeline: EdgarPipelineExecutionDep,
    user: CurrentUserDep,
    body: ExecuteRunOverrides | None = None,
) -> ExecuteRunResponse:
    """
    Run the deterministic EDGAR orchestration for this row (synchronous; may take minutes with SEC).

    Body fields override ``input_payload_json`` / ``orchestration_goal_text`` for this invocation only.
    """
    row = require_analysis_run_owned(db, run_id, user.id)
    if row.status == AnalysisRunStatus.queued:
        raise HTTPException(
            status_code=409,
            detail="Run is queued for background execution; wait for the worker or use synchronous create",
        )
    if row.status == AnalysisRunStatus.running:
        raise HTTPException(
            status_code=409,
            detail="Run is already executing",
        )
    guard_run_admission(db, user, requested_engine=_requested_engine(row.input_payload_json))
    engine = select_run_engine(row, get_settings())
    tc = getattr(request.state, "trace_carrier_for_jobs", None)
    api_tracer = get_tracer("backend.api.runs")
    try:
        with attach_trace_carrier(tc):
            bind_current_trace_for_logs()
            with api_tracer.start_as_current_span(
                "runs.dispatch_execute",
                attributes={"analysis.run.id": str(run_id), "run.engine": engine},
            ):
                bind_current_trace_for_logs()
                if engine == ENGINE_AGENTIC:
                    agentic = AgenticInvestigationExecutionService(db)
                    result = agentic.execute_analysis_run(
                        run_id,
                        analysis_goal=body.analysis_goal if body else None,
                    )
                    return ExecuteRunResponse(
                        analysis_run_id=run_id,
                        orchestration_run_id=result.investigation_id,
                        orchestration_status=result.investigation_status.value,
                        message=result.message,
                        final_summary=result.final_summary,
                        artifact_count=0,
                        db_status=result.db_status,
                    )
                out = pipeline.execute_analysis_run(
                    run_id,
                    tickers=body.tickers if body else None,
                    analysis_goal=body.analysis_goal if body else None,
                    refresh=body.refresh if body else None,
                )
    except RunCancelledDuringExecution as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ExecuteRunResponse(
        analysis_run_id=run_id,
        orchestration_run_id=str(out.run_id),
        orchestration_status=out.status.value,
        message=out.message,
        final_summary=out.final_summary or "",
        artifact_count=len(out.artifact_paths),
        db_status=AnalysisRunStatus(out.status.value),
    )
