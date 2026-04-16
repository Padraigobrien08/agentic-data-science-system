"""Cancel and retry analysis runs with atomic job row updates."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.domain.status_transitions import is_retriable_terminal, is_terminal_analysis_run
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.analysis_run_service import AnalysisRunService
from backend.observability.tracing import serialize_trace_carrier
from backend.services.exceptions import RunLifecycleError


class RunLifecycleService:
    def __init__(
        self,
        session: Session,
        *,
        runs: AnalysisRunService | None = None,
        jobs: RunExecutionJobRepository | None = None,
    ) -> None:
        self._session = session
        self._runs = runs if runs is not None else AnalysisRunService(session)
        self._jobs = jobs if jobs is not None else RunExecutionJobRepository(session)

    def cancel_analysis_run(self, analysis_run_id: UUID) -> AnalysisRun:
        row = self._runs.get(analysis_run_id)
        if row is None:
            raise RunLifecycleError("Run not found", status_code=404)
        if is_terminal_analysis_run(row.status):
            raise RunLifecycleError(
                f"Run is already finished ({row.status.value})",
                status_code=409,
            )
        if row.status == AnalysisRunStatus.pending:
            self._runs.transition_status(analysis_run_id, AnalysisRunStatus.cancelled)
            self._jobs.flush()
            return self._runs.require(analysis_run_id)
        if row.status == AnalysisRunStatus.queued:
            self._jobs.cancel_open_jobs_for_run(analysis_run_id, reason="Cancelled by user")
            self._runs.transition_status(analysis_run_id, AnalysisRunStatus.cancelled)
            self._jobs.flush()
            return self._runs.require(analysis_run_id)
        if row.status == AnalysisRunStatus.running:
            self._jobs.cancel_open_jobs_for_run(analysis_run_id, reason="Cancelled by user")
            self._runs.set_error_summary(analysis_run_id, "Cancelled by user")
            self._runs.transition_status(analysis_run_id, AnalysisRunStatus.cancelled)
            self._jobs.flush()
            return self._runs.require(analysis_run_id)
        raise RunLifecycleError(
            f"Run cannot be cancelled from status {row.status.value!r}",
            status_code=409,
        )

    def retry_analysis_run(
        self,
        analysis_run_id: UUID,
        *,
        overrides: dict[str, Any] | None = None,
        trace_carrier: dict[str, str] | None = None,
    ) -> AnalysisRun:
        row = self._runs.get(analysis_run_id)
        if row is None:
            raise RunLifecycleError("Run not found", status_code=404)
        if row.status == AnalysisRunStatus.success:
            raise RunLifecycleError("Successful runs cannot be retried", status_code=409)
        if row.status == AnalysisRunStatus.queued:
            raise RunLifecycleError(
                "Run is already queued for execution",
                status_code=409,
            )
        if row.status in (AnalysisRunStatus.pending, AnalysisRunStatus.running):
            raise RunLifecycleError(
                f"Run cannot be retried from status {row.status.value!r}",
                status_code=409,
            )
        if not is_retriable_terminal(row.status):
            raise RunLifecycleError(
                f"Run cannot be retried from status {row.status.value!r}",
                status_code=409,
            )
        if self._jobs.has_open_job_for_run(analysis_run_id):
            raise RunLifecycleError(
                "An execution job is already in progress or pending for this run",
                status_code=409,
            )
        self._runs.transition_status(analysis_run_id, AnalysisRunStatus.queued)
        self._runs.set_error_summary(analysis_run_id, None)
        tc = trace_carrier if trace_carrier is not None else serialize_trace_carrier()
        latest = self._jobs.get_latest_for_run(analysis_run_id)
        next_attempt = latest.attempt_count + 1 if latest is not None else 1
        self._jobs.create_pending_attempt(
            analysis_run_id=analysis_run_id,
            attempt_count=next_attempt,
            overrides_json=overrides,
            trace_context_json=tc,
        )
        return self._runs.require(analysis_run_id)

    def build_status_view(
        self,
        analysis_run_id: UUID,
    ) -> tuple[AnalysisRun, bool, RunExecutionJob | None, list[RunExecutionJob]]:
        row = self._runs.get(analysis_run_id)
        if row is None:
            raise RunLifecycleError("Run not found", status_code=404)
        has_open = self._jobs.has_open_job_for_run(analysis_run_id)
        history = self._jobs.list_for_run(analysis_run_id)
        latest = history[0] if history else None
        return row, has_open, latest, history
