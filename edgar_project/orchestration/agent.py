"""
Phase 3 **coordinator** (in-process): validate → plan → execute → structured result.

This module is the thin driver between user input and planner/executor. It does not
implement planning rules or MCP execution—those live in :class:`~edgar_project.orchestration.planner.Planner`
and :class:`~edgar_project.orchestration.executor.Executor`.

**Coordinator responsibilities** (everything else is delegated):

1. Validate :class:`~edgar_project.orchestration.schemas.OrchestrationInput` (entrypoints) or accept pre-validated input (:meth:`AnalysisAgent.run`).
2. Allocate a ``run_id`` for correlation and logging.
3. Log run start (tickers, refresh, goal preview).
4. Invoke :class:`~edgar_project.orchestration.planner.Planner` ``build_plan``.
5. On planning failure: build terminal :class:`~edgar_project.orchestration.schemas.OrchestrationOutput` (``planning_failed`` interpreted goal), attach coordinator ``final_summary``, call ``log_run_finished`` (executor never runs).
6. On success: log plan summary (via planner ``describe_plan``—wording owned by planner), build :class:`~edgar_project.orchestration.execution_contract.ExecutionRequest`, invoke :class:`~edgar_project.orchestration.executor.Executor` ``run``.
7. On execution success: set ``final_summary`` (coordinator one-liner); executor already logged ``log_run_finished``.

**Not** coordinator responsibilities:

* Intent rules, plan shape, or step lists → :class:`~edgar_project.orchestration.planner.Planner`.
* MCP calls, partial success vs terminal status, step envelopes → :class:`~edgar_project.orchestration.executor.Executor`.

**Boundaries**

* :class:`OrchestrationInput` is validated at the public entrypoint (:func:`run_analysis_agent`) and passed through unchanged to the planner.
* :class:`~edgar_project.orchestration.execution_contract.ExecutionRequest` carries planner output + ``run_id`` to the executor; the executor does not re-parse ``analysis_goal``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import uuid4

from edgar_project.orchestration.execution_contract import ExecutionRequest
from edgar_project.orchestration.executor import Executor
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.state import OrchestrationRunState
from edgar_project.orchestration.run_logging import log_run_finished, logger
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationRunStatus,
    PlanningOutcome,
)


def _build_final_summary_line(out: OrchestrationOutput) -> str:
    """Single-line recap for ``OrchestrationOutput.final_summary`` (coordinator-owned copy)."""
    if out.step_statuses:
        step_part = " → ".join(f"{e.tool_name}={e.mcp_status}" for e in out.step_statuses)
    else:
        step_part = " → ".join(s.tool_name for s in out.tool_call_sequence) or "—"
    warn_n, err_n = len(out.warnings), len(out.errors)
    meta = f"{err_n} error(s), {warn_n} warning(s)" if (err_n or warn_n) else "no issues"
    ig = out.interpreted_goal
    intent_part = f"intent={ig.intent.value}" if ig.intent else "intent=—"
    return f"{out.status.value}: {out.message} | {intent_part} | {meta} | steps: {step_part}"


def _orchestration_output_when_planning_fails(
    run_id: str, request: OrchestrationInput, outcome: PlanningOutcome
) -> OrchestrationOutput:
    """Terminal output when the planner returns ``ok=False`` (executor is not invoked)."""
    err0 = outcome.errors[0] if outcome.errors else None
    ig = InterpretedGoal(
        code=InterpretedGoalCode.planning_failed,
        description="Planning did not produce an executable plan (validation or intent).",
        user_goal_text=request.analysis_goal.strip(),
    )
    out = OrchestrationOutput(
        run_id=run_id,
        status=OrchestrationRunStatus.error,
        message=err0.message if err0 else "Planning failed",
        interpreted_goal=ig,
        errors=list(outcome.errors),
        step_statuses=[],
    )
    out = out.model_copy(update={"final_summary": _build_final_summary_line(out)})
    log_run_finished(
        out.run_id,
        status=out.status,
        message=out.message,
        errors=list(out.errors),
        warnings_count=len(out.warnings),
        artifact_path_count=len(out.artifact_paths),
    )
    return out


class AnalysisAgent:
    """
    In-process **coordinator**: wires :class:`Planner` → :class:`ExecutionRequest` → :class:`Executor`.

    Injectable ``planner`` / ``executor`` are the extension points for tests or future workers;
    defaults match :func:`run_analysis_agent`.
    """

    def __init__(self, planner: Planner | None = None, executor: Executor | None = None) -> None:
        self._planner = planner or Planner()
        self._executor = executor or Executor()

    def run(self, request: OrchestrationInput) -> OrchestrationOutput:
        """Run the coordinator pipeline (caller supplies already-validated ``request``)."""
        out, _ = self.run_returning_state(request)
        return out

    def run_returning_state(
        self,
        request: OrchestrationInput,
    ) -> tuple[OrchestrationOutput, OrchestrationRunState | None]:
        """
        Plan, execute MCP steps via :class:`~edgar_project.orchestration.executor.Executor`, return output
        plus mutable :class:`~edgar_project.orchestration.state.OrchestrationRunState` when the executor ran.

        On planning failure the executor is not invoked and the second value is ``None``.
        """
        run_id = str(uuid4())
        goal_preview = request.analysis_goal.strip()[:240]
        logger.info(
            "[%s] run_start tickers=%s refresh=%s goal=%r",
            run_id,
            list(request.tickers),
            request.refresh,
            goal_preview,
        )

        outcome = self._planner.build_plan(request)
        if not outcome.ok:
            logger.warning(
                "[%s] planning_failed code=%s message=%r",
                run_id,
                outcome.errors[0].code if outcome.errors else "unknown",
                outcome.errors[0].message if outcome.errors else "",
            )
            return _orchestration_output_when_planning_fails(run_id, request, outcome), None

        assert outcome.plan is not None
        logger.info(
            "[%s] plan_ready steps=%d\n%s",
            run_id,
            len(outcome.plan.steps),
            self._planner.describe_plan(outcome.plan),
        )

        execution = ExecutionRequest.from_planning(run_id=run_id, request=request, outcome=outcome)
        out, state = self._executor.run_returning_state(execution)
        return out.model_copy(update={"final_summary": _build_final_summary_line(out)}), state


def run_analysis_agent(request: OrchestrationInput | Mapping[str, Any]) -> OrchestrationOutput:
    """
    Public entry: validate ``request``, then run the coordinator (:class:`AnalysisAgent`).

    Validation is Pydantic-only here; business rules for tickers/goals remain in :class:`Planner`.
    ``tool_call_sequence`` lists tools actually run; ``final_summary`` is the coordinator one-liner.
    """
    validated = OrchestrationInput.model_validate(request)
    return AnalysisAgent().run(validated)


def run_analysis_agent_returning_state(
    request: OrchestrationInput | Mapping[str, Any],
) -> tuple[OrchestrationOutput, OrchestrationRunState | None]:
    """Like :func:`run_analysis_agent` but also returns executor state for MCP envelope persistence."""
    validated = OrchestrationInput.model_validate(request)
    return AnalysisAgent().run_returning_state(validated)


def run_analysis(request: OrchestrationInput) -> OrchestrationOutput:
    """Backward-compatible alias for :func:`run_analysis_agent`."""
    return run_analysis_agent(request)
