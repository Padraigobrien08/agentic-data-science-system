"""
Execute the in-repo deterministic EDGAR orchestration pipeline against a persisted analysis run.

Delegates numerical work to :func:`edgar_project.orchestration.run_analysis_agent` (no rewrites).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.models.enums import AnalysisRunStatus
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from edgar_project.orchestration import OrchestrationInput, run_analysis_agent
from edgar_project.orchestration.schemas import OrchestrationOutput, OrchestrationRunStatus
from edgar_project.repo_layout import chdir_repo_root, ensure_repo_root_on_syspath


def _orch_status_to_db(status: OrchestrationRunStatus) -> AnalysisRunStatus:
    return AnalysisRunStatus(status.value)


def _build_orchestration_input(
    *,
    input_payload: Mapping[str, Any] | list | None,
    orchestration_goal_text: str | None,
    overrides_tickers: list[str] | None,
    overrides_goal: str | None,
    overrides_refresh: bool | None,
) -> OrchestrationInput:
    payload: dict[str, Any] = input_payload if isinstance(input_payload, dict) else {}
    tickers = list(overrides_tickers) if overrides_tickers is not None else list(payload.get("tickers") or [])
    if tickers:
        tickers = [str(t).strip().upper() for t in tickers if str(t).strip()]
    goal = (
        overrides_goal
        if overrides_goal is not None
        else (payload.get("analysis_goal") or orchestration_goal_text or "")
    )
    if not isinstance(goal, str) or not goal.strip():
        raise ValueError("analysis_goal is required (set on the run or in input_payload_json)")
    refresh = overrides_refresh if overrides_refresh is not None else bool(payload.get("refresh", False))
    return OrchestrationInput(tickers=tickers, analysis_goal=goal.strip(), refresh=refresh)


_EXECUTABLE_STATUSES: frozenset[AnalysisRunStatus] = frozenset(
    {
        AnalysisRunStatus.pending,
        AnalysisRunStatus.error,
        AnalysisRunStatus.partial_success,
        AnalysisRunStatus.no_data,
        AnalysisRunStatus.cancelled,
    }
)


class EdgarPipelineExecutionService:
    """
    Run :func:`~edgar_project.orchestration.run_analysis_agent` for a DB row and persist outcomes.

    Uses :class:`~edgar_project.repo_layout.chdir_repo_root` so ``config`` / MCP paths match the CLI.

    Commits the SQLAlchemy session on success and after persisting a failure transition so API callers
    do not lose error state on rollback.
    """

    def __init__(
        self,
        session: Session,
        *,
        run_service: AnalysisRunService | None = None,
        artifact_service: ArtifactService | None = None,
        agent_runner: Callable[[OrchestrationInput | Mapping[str, Any]], OrchestrationOutput] | None = None,
    ) -> None:
        self._session = session
        self._runs = run_service or AnalysisRunService(self._session)
        self._artifacts = artifact_service or ArtifactService(self._session)
        self._agent_runner = agent_runner or run_analysis_agent

    def execute_analysis_run(
        self,
        analysis_run_id: UUID,
        *,
        tickers: list[str] | None = None,
        analysis_goal: str | None = None,
        refresh: bool | None = None,
    ) -> OrchestrationOutput:
        """
        Mark run *running*, invoke orchestration, map terminal status, persist output JSON and artifacts.

        Raises:
            ValueError: unknown run, not executable, or invalid orchestration input.
        """
        row = self._runs.require(analysis_run_id)
        if row.status == AnalysisRunStatus.running:
            raise ValueError("Run is already executing (stale running state)")
        if row.status not in _EXECUTABLE_STATUSES:
            raise ValueError(f"Run status {row.status.value!r} is not executable")

        orch_in = _build_orchestration_input(
            input_payload=row.input_payload_json,
            orchestration_goal_text=row.orchestration_goal_text,
            overrides_tickers=tickers,
            overrides_goal=analysis_goal,
            overrides_refresh=refresh,
        )

        self._runs.transition_status(analysis_run_id, AnalysisRunStatus.running)
        self._session.flush()

        ensure_repo_root_on_syspath()
        chdir_repo_root()

        try:
            out = self._agent_runner(orch_in)
        except Exception as exc:
            self._runs.set_error_summary(analysis_run_id, str(exc))
            self._runs.transition_status(analysis_run_id, AnalysisRunStatus.error)
            self._session.flush()
            self._session.commit()
            raise

        db_terminal = _orch_status_to_db(out.status)
        row = self._runs.require(analysis_run_id)
        if out.run_id:
            row.correlation_id = str(out.run_id)[:64]
        self._runs.set_output_payload(analysis_run_id, out.model_dump(mode="json"))
        if out.errors:
            self._runs.set_error_summary(analysis_run_id, out.errors[0].message)
        else:
            self._runs.set_error_summary(analysis_run_id, None)

        for role_key, path_str in out.artifact_paths.items():
            if not path_str or not str(path_str).strip():
                continue
            p = Path(str(path_str))
            if not p.is_file():
                continue
            try:
                self._artifacts.ingest_pipeline_file(
                    p,
                    role_key=role_key,
                    analysis_run_id=analysis_run_id,
                    meta_json={"orchestration_run_id": out.run_id, "source": "pipeline"},
                )
            except (OSError, ValueError):
                continue

        self._runs.transition_status(analysis_run_id, db_terminal)
        self._session.flush()
        self._session.commit()
        return out
