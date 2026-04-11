"""Analysis run CRUD and synchronous EDGAR execution (Phase A)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.exc import IntegrityError

from backend.api.deps import (
    AnalysisRunServiceDep,
    ArtifactServiceDep,
    DbSession,
    EdgarPipelineExecutionDep,
    RunStepServiceDep,
)
from backend.models.project import Project
from backend.models.enums import AnalysisRunStatus
from backend.schemas.analysis_run import AnalysisRunCreate
from backend.schemas.run_lifecycle import (
    AnalysisRunStatusResponse,
    RunRetryRequest,
    analysis_run_status_to_response,
)
from backend.schemas.api_phase_a import (
    AnalysisRunDetailResponse,
    AnalysisRunSummary,
    ArtifactMetadata,
    RunStepDetailItem,
    analysis_run_to_detail,
    analysis_run_to_summary,
    artifact_to_metadata,
    run_step_to_detail,
)
from backend.schemas.execute_run import ExecuteRunOverrides, ExecuteRunResponse
from backend.services.exceptions import InvalidStatusTransition, RunLifecycleError
from backend.services.run_lifecycle_service import RunLifecycleService
from backend.services.run_queue_service import RunQueueService

router = APIRouter(prefix="/runs", tags=["runs"])


@router.post("", response_model=AnalysisRunSummary, status_code=201)
def create_run(
    body: AnalysisRunCreate,
    db: DbSession,
    run_svc: AnalysisRunServiceDep,
) -> AnalysisRunSummary:
    """Create an analysis run in ``pending`` (orchestration execution is not started here)."""
    if db.get(Project, body.project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    try:
        row = run_svc.create(
            body.project_id,
            initiated_by_user_id=body.initiated_by_user_id,
            correlation_id=body.correlation_id,
            orchestration_goal_text=body.orchestration_goal_text,
            input_payload_json=body.input_payload_json,
            meta_json=body.meta_json,
        )
        if body.enqueue_execution:
            overrides = (
                body.enqueue_overrides.model_dump(exclude_none=True) if body.enqueue_overrides else None
            )
            RunQueueService(db).enqueue_after_create(row.id, overrides)
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
    project_id: UUID = Query(..., description="Filter runs for this project"),
) -> list[AnalysisRunSummary]:
    """List runs for a project (newest first)."""
    if db.get(Project, project_id) is None:
        raise HTTPException(status_code=404, detail="Project not found")
    rows = run_svc.list_for_project(project_id)
    return [analysis_run_to_summary(r) for r in rows]


@router.get("/{run_id}/status", response_model=AnalysisRunStatusResponse)
def get_run_status(run_id: UUID, db: DbSession) -> AnalysisRunStatusResponse:
    """Execution-focused status: terminal flag, open job, and latest job snapshot."""
    try:
        row, has_open, latest = RunLifecycleService(db).build_status_view(run_id)
    except RunLifecycleError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    return analysis_run_status_to_response(
        row,
        has_open_execution_job=has_open,
        latest_execution_job=latest,
    )


@router.post("/{run_id}/cancel", response_model=AnalysisRunSummary)
def cancel_run(run_id: UUID, db: DbSession) -> AnalysisRunSummary:
    """Cancel a ``pending`` or ``queued`` run (not ``running`` or terminal)."""
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
    db: DbSession,
    body: RunRetryRequest | None = None,
) -> AnalysisRunSummary:
    """Re-queue a finished non-success run for background execution."""
    overrides = (
        body.enqueue_overrides.model_dump(exclude_none=True)
        if body is not None and body.enqueue_overrides is not None
        else None
    )
    try:
        row = RunLifecycleService(db).retry_analysis_run(run_id, overrides=overrides)
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
    run_svc: AnalysisRunServiceDep,
    include_payloads: bool = Query(
        False,
        description="When true, include input_payload_json, output_payload_json, and meta_json",
    ),
) -> AnalysisRunDetailResponse:
    row = run_svc.get(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
    return analysis_run_to_detail(row, include_payloads=include_payloads)


@router.get("/{run_id}/steps", response_model=list[RunStepDetailItem])
def list_run_steps(
    run_id: UUID,
    db: DbSession,
    run_svc: AnalysisRunServiceDep,
    step_svc: RunStepServiceDep,
    include_payloads: bool = Query(
        False,
        description="When true, include planner_tool_input_json and meta_json per step",
    ),
) -> list[RunStepDetailItem]:
    if run_svc.get(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    steps = step_svc.list_for_analysis_run(run_id)
    return [run_step_to_detail(s, include_payloads=include_payloads) for s in steps]


@router.get("/{run_id}/artifacts", response_model=list[ArtifactMetadata])
def list_run_artifacts(
    run_id: UUID,
    run_svc: AnalysisRunServiceDep,
    art_svc: ArtifactServiceDep,
) -> list[ArtifactMetadata]:
    if run_svc.get(run_id) is None:
        raise HTTPException(status_code=404, detail="Run not found")
    rows = art_svc.list_for_analysis_run(run_id)
    return [artifact_to_metadata(a) for a in rows]


@router.post("/{run_id}/execute", response_model=ExecuteRunResponse)
def execute_run(
    run_id: UUID,
    pipeline: EdgarPipelineExecutionDep,
    run_svc: AnalysisRunServiceDep,
    body: ExecuteRunOverrides | None = None,
) -> ExecuteRunResponse:
    """
    Run the deterministic EDGAR orchestration for this row (synchronous; may take minutes with SEC).

    Body fields override ``input_payload_json`` / ``orchestration_goal_text`` for this invocation only.
    """
    row = run_svc.get(run_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Run not found")
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
    try:
        out = pipeline.execute_analysis_run(
            run_id,
            tickers=body.tickers if body else None,
            analysis_goal=body.analysis_goal if body else None,
            refresh=body.refresh if body else None,
        )
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
