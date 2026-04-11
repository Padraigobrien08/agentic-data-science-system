"""
Execute the in-repo deterministic EDGAR orchestration pipeline against a persisted analysis run.

Uses :func:`backend.agents.traceable_analysis_pipeline.run_traceable_edgar_pipeline` so MCP steps,
LLM critic/report (when configured), and envelopes are persisted in the analysis run session.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from backend.agents.traceable_analysis_pipeline import run_traceable_edgar_pipeline
from backend.llm.exceptions import LLMProviderConfigurationError
from backend.llm.factory import get_chat_completion_provider
from backend.models.enums import AnalysisRunStatus
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from edgar_project.orchestration import OrchestrationInput
from edgar_project.orchestration.agent import AnalysisAgent
from edgar_project.orchestration.schemas import OrchestrationOutput, OrchestrationRunStatus
from edgar_project.orchestration.state import OrchestrationRunState
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
    Run traceable orchestration (MCP + optional critic/report LLMs) for a DB row and persist outcomes.

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
        orchestration_with_state: Callable[
            [OrchestrationInput], tuple[OrchestrationOutput, OrchestrationRunState | None]
        ]
        | None = None,
    ) -> None:
        self._session = session
        self._runs = run_service or AnalysisRunService(self._session)
        self._artifacts = artifact_service or ArtifactService(self._session)
        if orchestration_with_state is not None:
            self._coord = orchestration_with_state
        elif agent_runner is not None:

            def _legacy(inp: OrchestrationInput) -> tuple[OrchestrationOutput, OrchestrationRunState | None]:
                return agent_runner(inp), None

            self._coord = _legacy
        else:
            self._analysis_agent = AnalysisAgent()
            self._coord = self._analysis_agent.run_returning_state

    def execute_analysis_run(
        self,
        analysis_run_id: UUID,
        *,
        tickers: list[str] | None = None,
        analysis_goal: str | None = None,
        refresh: bool | None = None,
        from_worker: bool = False,
    ) -> OrchestrationOutput:
        """
        Mark run *running*, invoke orchestration, map terminal status, persist output JSON and artifacts.

        When ``from_worker`` is True, the run must be ``queued`` (background job claim). The API
        synchronous ``/execute`` path must use ``from_worker=False``.

        Raises:
            ValueError: unknown run, not executable, or invalid orchestration input.
        """
        row = self._runs.require(analysis_run_id)
        if from_worker:
            if row.status != AnalysisRunStatus.queued:
                raise ValueError(
                    f"Worker execution requires status 'queued', got {row.status.value!r}"
                )
        else:
            if row.status == AnalysisRunStatus.running:
                raise ValueError("Run is already executing (stale running state)")
            if row.status == AnalysisRunStatus.queued:
                raise ValueError(
                    "Run is queued for background execution; use the worker or create without enqueue"
                )
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

        traced = None
        try:
            try:
                llm_provider = get_chat_completion_provider()
            except LLMProviderConfigurationError:
                llm_provider = None
            traced = run_traceable_edgar_pipeline(
                self._session,
                analysis_run_id,
                orch_in,
                llm_provider=llm_provider,
                coordinator=self._coord,
            )
            out = traced.orchestration_output
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
        if traced is not None and traced.output_payload_patch:
            self._runs.merge_output_payload(analysis_run_id, traced.output_payload_patch)
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
