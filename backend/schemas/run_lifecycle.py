"""Cancel, retry, and status snapshot schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from backend.domain.status_transitions import is_terminal_analysis_run
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.schemas.analysis_run import RunEnqueueOverrides
from backend.schemas.common import OrmSchema


class RunRetryRequest(OrmSchema):
    """Optional overrides for the retried execution (same as enqueue)."""

    enqueue_overrides: RunEnqueueOverrides | None = None


class RunJobStatusSnapshot(BaseModel):
    """Latest execution job row for a run (may be completed or in-flight)."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    status: RunExecutionJobStatus
    error_detail: str | None = None
    claimed_at: datetime | None = None
    created_at: datetime


class AnalysisRunStatusResponse(BaseModel):
    """Focused view for polling — run lifecycle + execution queue state."""

    analysis_run_id: UUID
    project_id: UUID
    status: AnalysisRunStatus
    is_terminal: bool
    error_summary: str | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None
    has_open_execution_job: bool
    latest_execution_job: RunJobStatusSnapshot | None = None


def analysis_run_status_to_response(
    row: AnalysisRun,
    *,
    has_open_execution_job: bool,
    latest_execution_job: RunExecutionJob | None,
) -> AnalysisRunStatusResponse:
    return AnalysisRunStatusResponse(
        analysis_run_id=row.id,
        project_id=row.project_id,
        status=row.status,
        is_terminal=is_terminal_analysis_run(row.status),
        error_summary=row.error_summary,
        started_at=row.started_at,
        finished_at=row.finished_at,
        has_open_execution_job=has_open_execution_job,
        latest_execution_job=RunJobStatusSnapshot.model_validate(latest_execution_job)
        if latest_execution_job is not None
        else None,
    )
