"""
Orchestration **contract stability** — lightweight guards for a future planner/executor split.

No live SEC/MCP; focuses on constants, serialization, and coordinator/executor boundaries.
"""

from __future__ import annotations

import json
from typing import get_type_hints
from unittest.mock import MagicMock

import pytest

from edgar_project.orchestration.agent import AnalysisAgent
from edgar_project.orchestration.constants import (
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
from edgar_project.orchestration.execution_contract import ExecutionRequest, ExecutionResult
from edgar_project.orchestration.executor import Executor
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import (
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationPlan,
    OrchestrationRunStatus,
    PlannedStep,
)
from edgar_project.orchestration.state import OrchestrationRunState

_ALL_TOOL_NAMES: frozenset[str] = frozenset(
    {
        TOOL_RESOLVE_COMPANY,
        TOOL_FETCH_COMPANY_DATA,
        TOOL_BUILD_PANEL,
        TOOL_COMPUTE_FEATURES,
        TOOL_DETECT_ANOMALIES,
        TOOL_GENERATE_REPORT,
        TOOL_RUN_PIPELINE,
    }
)


def test_terminal_status_constants_match_schema_enum() -> None:
    """OrchestrationRunStatus string values stay aligned with ``constants.ORCH_STATUS_*``."""
    assert OrchestrationRunStatus.success.value == ORCH_STATUS_SUCCESS
    assert OrchestrationRunStatus.partial_success.value == ORCH_STATUS_PARTIAL_SUCCESS
    assert OrchestrationRunStatus.no_data.value == ORCH_STATUS_NO_DATA
    assert OrchestrationRunStatus.error.value == ORCH_STATUS_ERROR
    assert {e.value for e in OrchestrationRunStatus} == {
        ORCH_STATUS_SUCCESS,
        ORCH_STATUS_PARTIAL_SUCCESS,
        ORCH_STATUS_NO_DATA,
        ORCH_STATUS_ERROR,
    }


def test_step_status_constants_distinct_and_documented() -> None:
    """Step-level vocabulary used in outputs vs MCP vs skip remains a stable, disjoint set."""
    mcp = {STEP_STATUS_MCP_SUCCESS, STEP_STATUS_MCP_NO_DATA, STEP_STATUS_MCP_ERROR}
    assert len(mcp) == 3
    assert STEP_STATUS_SKIPPED not in mcp


def test_planner_emits_only_centralized_tool_names() -> None:
    """Plans must not introduce ad-hoc tool name strings outside the shared constant set."""
    out = Planner().build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.ok and out.plan
    for step in out.plan.steps:
        assert step.tool_name in _ALL_TOOL_NAMES


def test_run_state_round_trip_preserves_tool_names_and_contract_version() -> None:
    """JSON dump/validate preserves plan steps and run-state contract id (split-friendly)."""
    req = OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)
    plan = OrchestrationPlan(
        steps=[
            PlannedStep(
                order=0,
                tool_name=TOOL_RESOLVE_COMPANY,
                tool_input={"ticker": "AAPL"},
                label="resolve_company:AAPL",
            )
        ]
    )
    st = OrchestrationRunState(request=req, plan=plan)
    st2 = OrchestrationRunState.model_validate_json(json.dumps(st.model_dump(mode="json")))
    assert st2.contract_version == ORCH_RUN_STATE_CONTRACT_VERSION
    assert st2.plan is not None
    assert st2.plan.steps[0].tool_name == TOOL_RESOLVE_COMPANY


def test_planning_outcome_maps_to_execution_request_shape() -> None:
    """Successful :class:`PlanningOutcome` fields copy into :class:`ExecutionRequest` without loss."""
    request = OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)
    outcome = Planner().build_plan(request)
    assert outcome.ok and outcome.plan is not None and outcome.interpreted_goal is not None

    ex = ExecutionRequest.from_planning(run_id="stable-run-id", request=request, outcome=outcome)
    assert ex.run_id == "stable-run-id"
    assert ex.request is request
    assert ex.plan == outcome.plan
    assert ex.interpreted_goal == outcome.interpreted_goal
    st = ex.to_run_state()
    assert st.plan == outcome.plan
    assert st.interpreted_goal == outcome.interpreted_goal


def test_coordinator_does_not_invoke_executor_on_planning_failure() -> None:
    """Planning failure path returns before ``Executor.run`` (no MCP layer)."""
    mock_executor = MagicMock(spec=Executor)
    agent = AnalysisAgent(executor=mock_executor)
    out = agent.run(
        OrchestrationInput(
            tickers=["A", "B", "C", "D", "E", "F"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    mock_executor.run.assert_not_called()
    assert out.status == OrchestrationRunStatus.error
    assert out.interpreted_goal.code == InterpretedGoalCode.planning_failed


def test_executor_run_parameter_is_execution_request_contract() -> None:
    """Executor public API stays tied to :class:`ExecutionRequest` / :class:`ExecutionResult`."""
    hints = get_type_hints(Executor.run, include_extras=True)
    assert hints["execution"] is ExecutionRequest
    assert hints["return"] is ExecutionResult


@pytest.mark.parametrize(
    "status",
    [
        OrchestrationRunStatus.success,
        OrchestrationRunStatus.partial_success,
        OrchestrationRunStatus.no_data,
        OrchestrationRunStatus.error,
    ],
)
def test_orchestration_output_accepts_each_terminal_status(status: OrchestrationRunStatus) -> None:
    """Final response model accepts every defined terminal status (semantics stable for APIs)."""
    plan_out = Planner().build_plan(
        OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)
    )
    assert plan_out.ok and plan_out.interpreted_goal is not None
    out = OrchestrationOutput(run_id="x", status=status, message="m", interpreted_goal=plan_out.interpreted_goal)
    assert out.status == status
    assert out.status.value in {
        ORCH_STATUS_SUCCESS,
        ORCH_STATUS_PARTIAL_SUCCESS,
        ORCH_STATUS_NO_DATA,
        ORCH_STATUS_ERROR,
    }
