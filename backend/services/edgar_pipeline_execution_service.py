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

import structlog
from sqlalchemy.orm import Session

from backend.agents.intent_preferences_assistant import maybe_apply_llm_intent_preferences
from backend.agents.traceable_analysis_pipeline import run_traceable_edgar_pipeline
from backend.agents.llm_phase_status import maybe_llm_error_summary_note
from backend.agents.traceability_summary import enrich_traceability_artifact_ids
from backend.llm.exceptions import LLMProviderConfigurationError
from backend.llm.factory import get_chat_completion_provider
from backend.models.enums import AnalysisRunStatus
from backend.observability.context import (
    bind_run_context,
    clear_run_context,
    merge_orchestration_run_id,
)
from backend.observability.metrics import (
    monotonic_s,
    observe_pipeline_complete,
    observe_pipeline_exception,
)
from backend.observability.tracing import bind_current_trace_for_logs, get_tracer
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.artifact_service import ArtifactService
from backend.config.settings import get_settings
from backend.services.exceptions import RunCancelledDuringExecution
from edgar_project.orchestration import OrchestrationInput
from edgar_project.orchestration.agent import AnalysisAgent
from edgar_project.orchestration.schemas import OrchestrationOutput, OrchestrationRunStatus
from edgar_project.orchestration.state import OrchestrationRunState
from edgar_project.repo_layout import chdir_repo_root, ensure_repo_root_on_syspath

log = structlog.get_logger(__name__)


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
        bind_run_context(
            analysis_run_id=analysis_run_id,
            component="pipeline",
            from_worker=from_worker,
        )
        bind_current_trace_for_logs()
        t0 = monotonic_s()
        pipeline_tracer = get_tracer("backend.pipeline")
        try:
            with pipeline_tracer.start_as_current_span(
                "pipeline.execute",
                attributes={
                    "analysis.run.id": str(analysis_run_id),
                    "edgar.from_worker": from_worker,
                },
            ):
                bind_current_trace_for_logs()
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

                settings = get_settings()
                try:
                    llm_provider_pref = get_chat_completion_provider()
                except LLMProviderConfigurationError:
                    llm_provider_pref = None
                orch_in = maybe_apply_llm_intent_preferences(
                    self._session,
                    analysis_run_id,
                    orch_in,
                    llm_provider=llm_provider_pref,
                    settings=settings,
                )

                self._runs.transition_status(analysis_run_id, AnalysisRunStatus.running)
                self._session.flush()
                row = self._runs.require(analysis_run_id)
                self._session.refresh(row)
                if row.status == AnalysisRunStatus.cancelled:
                    self._session.rollback()
                    raise RunCancelledDuringExecution(
                        "Run was cancelled before pipeline execution started"
                    )

                ensure_repo_root_on_syspath()
                chdir_repo_root()

                traced = None
                try:
                    try:
                        llm_provider = get_chat_completion_provider()
                    except LLMProviderConfigurationError as exc:
                        log.warning(
                            "llm_provider_skipped",
                            analysis_run_id=str(analysis_run_id),
                            detail=str(exc),
                        )
                        llm_provider = None
                    traced = run_traceable_edgar_pipeline(
                        self._session,
                        analysis_run_id,
                        orch_in,
                        llm_provider=llm_provider,
                        coordinator=self._coord,
                    )
                    out = traced.orchestration_output
                except RunCancelledDuringExecution:
                    raise
                except Exception as exc:
                    observe_pipeline_exception(exc)
                    self._session.rollback()
                    row_cancel = self._runs.get(analysis_run_id)
                    if row_cancel is not None and row_cancel.status == AnalysisRunStatus.cancelled:
                        log.info(
                            "pipeline_abort_cancelled",
                            analysis_run_id=str(analysis_run_id),
                            exc_type=type(exc).__name__,
                        )
                        raise RunCancelledDuringExecution(
                            "Run was cancelled while the pipeline was executing"
                        ) from exc
                    log.exception(
                        "pipeline_failed",
                        analysis_run_id=str(analysis_run_id),
                        exc_type=type(exc).__name__,
                    )
                    self._runs.set_error_summary(analysis_run_id, str(exc))
                    self._runs.transition_status(analysis_run_id, AnalysisRunStatus.error)
                    self._session.flush()
                    self._session.commit()
                    raise

                row = self._runs.require(analysis_run_id)
                self._session.refresh(row)
                if row.status == AnalysisRunStatus.cancelled:
                    self._session.rollback()
                    raise RunCancelledDuringExecution(
                        "Run was cancelled while the pipeline was executing"
                    )

                if out.run_id:
                    merge_orchestration_run_id(str(out.run_id))

                db_terminal = _orch_status_to_db(out.status)
                if out.run_id:
                    row.correlation_id = str(out.run_id)[:64]
                self._session.refresh(row)
                if row.status == AnalysisRunStatus.cancelled:
                    self._session.rollback()
                    raise RunCancelledDuringExecution(
                        "Run was cancelled before pipeline results were persisted"
                    )
                self._runs.set_output_payload(analysis_run_id, out.model_dump(mode="json"))
                if traced is not None and traced.output_payload_patch:
                    self._runs.merge_output_payload(analysis_run_id, traced.output_payload_patch)
                if out.errors:
                    self._runs.set_error_summary(analysis_run_id, out.errors[0].message)
                else:
                    self._runs.set_error_summary(analysis_run_id, None)

                self._session.refresh(row)
                if not out.errors:
                    opl = row.output_payload_json if isinstance(row.output_payload_json, dict) else {}
                    lps = opl.get("llm_phases_summary")
                    if isinstance(lps, dict):
                        llm_note = maybe_llm_error_summary_note(list(out.errors), lps)
                        if llm_note:
                            self._runs.set_error_summary(analysis_run_id, llm_note)

                duration_s = monotonic_s() - t0
                observe_pipeline_complete(duration_s, db_terminal.value)
                log.info(
                    "pipeline_completed",
                    analysis_run_id=str(analysis_run_id),
                    orchestration_run_id=str(out.run_id) if out.run_id else None,
                    duration_s=round(duration_s, 4),
                    orchestration_status=out.status.value,
                    db_terminal_status=db_terminal.value,
                    artifact_path_count=len(out.artifact_paths),
                )

                self._session.refresh(row)
                if row.status == AnalysisRunStatus.cancelled:
                    self._session.rollback()
                    raise RunCancelledDuringExecution(
                        "Run was cancelled before artifacts were ingested"
                    )

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

                enrich_traceability_artifact_ids(self._session, analysis_run_id)

                self._runs.transition_status(analysis_run_id, db_terminal)
                self._session.flush()
                self._session.commit()
                return out
        finally:
            clear_run_context()
