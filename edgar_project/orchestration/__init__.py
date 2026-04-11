"""
Phase 3 orchestration — coordinator (:class:`AnalysisAgent`) over Phase 2 MCP tools.

Public contract:
  - :class:`OrchestrationInput` — tickers, ``analysis_goal``, ``refresh``
  - :class:`OrchestrationIntent` / :func:`interpret_goal_intent` — rule-based NL intent (no LLM)
  - :class:`OrchestrationOutput` — status, message, ``final_summary``, interpreted goal (incl. intent), tools, artifacts, errors
  - :func:`run_analysis_agent` — validate input, then coordinator → planner → executor → output

MCP I/O lives in :class:`Executor`; planning in :class:`Planner`. Both are exported from this package.
"""

from __future__ import annotations

from pydantic import JsonValue

from edgar_project.orchestration.agent import (
    AnalysisAgent,
    run_analysis,
    run_analysis_agent,
    run_analysis_agent_returning_state,
)
from edgar_project.orchestration.execution_contract import ExecutionRequest, ExecutionResult
from edgar_project.orchestration.executor import Executor
from edgar_project.orchestration.constants import (
    DEFAULT_TICKERS_WHEN_INPUT_EMPTY,
    ORCH_RUN_STATE_CONTRACT_VERSION,
    ORCH_STATUS_ERROR,
    ORCH_STATUS_NO_DATA,
    ORCH_STATUS_PARTIAL_SUCCESS,
    ORCH_STATUS_SUCCESS,
    STEP_STATUS_MCP_ERROR,
    STEP_STATUS_MCP_NO_DATA,
    STEP_STATUS_MCP_SUCCESS,
    STEP_STATUS_SKIPPED,
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_GENERATE_REPORT,
    TOOL_RESOLVE_COMPANY,
    TOOL_RUN_PIPELINE,
)
from edgar_project.orchestration.intent import IntentInterpretation, interpret_goal_intent
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.run_logging import log_run_finished, logger as orchestration_logger, tool_summary_line
from edgar_project.orchestration.schemas import (
    CODE_ORCH_DISPATCH,
    CODE_ORCH_UNSUPPORTED_GOAL,
    CODE_ORCH_VALIDATION,
    InterpretedGoal,
    InterpretedGoalCode,
    JsonDict,
    OrchestrationIntent,
    OrchestrationError,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationPlan,
    OrchestrationRunStatus,
    OrchestrationWarning,
    PlannedStep,
    PlanningOutcome,
    ResolvedCompany,
    StepRecord,
    StepStatusEntry,
    ToolCallStep,
    ToolParamValue,
    ToolResultSummary,
)
from edgar_project.orchestration.state import OrchestrationRunState

__all__ = [
    "AnalysisAgent",
    "CODE_ORCH_DISPATCH",
    "CODE_ORCH_UNSUPPORTED_GOAL",
    "CODE_ORCH_VALIDATION",
    "DEFAULT_TICKERS_WHEN_INPUT_EMPTY",
    "ExecutionRequest",
    "ExecutionResult",
    "Executor",
    "JsonDict",
    "JsonValue",
    "ORCH_RUN_STATE_CONTRACT_VERSION",
    "ORCH_STATUS_ERROR",
    "ORCH_STATUS_NO_DATA",
    "ORCH_STATUS_PARTIAL_SUCCESS",
    "ORCH_STATUS_SUCCESS",
    "IntentInterpretation",
    "Planner",
    "STEP_STATUS_MCP_ERROR",
    "STEP_STATUS_MCP_NO_DATA",
    "STEP_STATUS_MCP_SUCCESS",
    "STEP_STATUS_SKIPPED",
    "TOOL_BUILD_PANEL",
    "TOOL_COMPUTE_FEATURES",
    "TOOL_DETECT_ANOMALIES",
    "TOOL_FETCH_COMPANY_DATA",
    "TOOL_GENERATE_REPORT",
    "TOOL_RESOLVE_COMPANY",
    "TOOL_RUN_PIPELINE",
    "InterpretedGoal",
    "InterpretedGoalCode",
    "OrchestrationIntent",
    "OrchestrationError",
    "OrchestrationInput",
    "OrchestrationOutput",
    "OrchestrationPlan",
    "OrchestrationRunState",
    "OrchestrationRunStatus",
    "OrchestrationWarning",
    "PlannedStep",
    "PlanningOutcome",
    "ResolvedCompany",
    "StepRecord",
    "StepStatusEntry",
    "ToolCallStep",
    "ToolParamValue",
    "ToolResultSummary",
    "run_analysis",
    "run_analysis_agent",
    "run_analysis_agent_returning_state",
    "interpret_goal_intent",
    "log_run_finished",
    "orchestration_logger",
    "tool_summary_line",
]
