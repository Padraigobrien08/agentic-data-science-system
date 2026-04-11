"""Enqueue analysis runs for background worker execution."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.enums import AnalysisRunStatus, RunExecutionJobStatus
from backend.models.run_execution_job import RunExecutionJob
from backend.repositories.run_execution_job_repository import RunExecutionJobRepository
from backend.services.analysis_run_service import AnalysisRunService


class RunQueueService:
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

    def enqueue_after_create(self, analysis_run_id: UUID, overrides: dict[str, Any] | None) -> None:
        """Move ``pending`` → ``queued`` and insert a pending :class:`~backend.models.run_execution_job.RunExecutionJob`."""
        row = self._runs.require(analysis_run_id)
        if row.status != AnalysisRunStatus.pending:
            raise ValueError(f"Can only enqueue a pending run, got {row.status.value!r}")
        self._runs.transition_status(analysis_run_id, AnalysisRunStatus.queued)
        job = RunExecutionJob(
            analysis_run_id=analysis_run_id,
            status=RunExecutionJobStatus.pending,
            overrides_json=overrides,
        )
        self._jobs.add(job)
        self._jobs.flush()
