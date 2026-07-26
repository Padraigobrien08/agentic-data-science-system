"""Planner → executor handoff and LLM plan validation."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from backend.agents.boundary_failures import classify_llm_phase_exception
from backend.agents.errors import AgentFailureCode, AgentOutputError
from backend.agents.llm_plan_handoff import validate_llm_planned_steps_for_handoff
from backend.llm.exceptions import ChatCompletionProviderError
from edgar_project.orchestration.agent import AnalysisAgent
from edgar_project.orchestration.execution_contract import ExecutionRequest
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationPlan,
    OrchestrationRunStatus,
    PlannedStep,
    PlanningOutcome,
)


def test_execution_request_rejects_empty_plan() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="x",
        user_goal_text="goal",
    )
    outcome = PlanningOutcome(
        ok=True,
        plan=OrchestrationPlan(steps=[]),
        interpreted_goal=ig,
        errors=[],
    )
    inp = OrchestrationInput(tickers=["AAPL"], analysis_goal="test", refresh=False)
    with pytest.raises(ValueError, match="empty plan"):
        ExecutionRequest.from_planning(run_id="r1", request=inp, outcome=outcome)


def test_validate_llm_planned_steps_rejects_empty() -> None:
    with pytest.raises(AgentOutputError) as ei:
        validate_llm_planned_steps_for_handoff([])
    assert ei.value.code == AgentFailureCode.MODEL_SEMANTIC


def test_validate_llm_planned_steps_rejects_non_contiguous_orders() -> None:
    steps = [
        PlannedStep(order=1, tool_name="run_pipeline", tool_input={}, label="a"),
    ]
    with pytest.raises(AgentOutputError, match="contiguous"):
        validate_llm_planned_steps_for_handoff(steps)


def test_validate_llm_planned_steps_rejects_unknown_tool() -> None:
    steps = [
        PlannedStep(order=0, tool_name="not_a_real_mcp_tool", tool_input={}, label="a"),
    ]
    with pytest.raises(AgentOutputError, match="disallowed tool"):
        validate_llm_planned_steps_for_handoff(steps)


def test_classify_llm_phase_exception() -> None:
    assert (
        classify_llm_phase_exception(
            AgentOutputError("x", code=AgentFailureCode.MODEL_JSON),
        )
        == "model_output_invalid_json"
    )
    assert classify_llm_phase_exception(ChatCompletionProviderError("rate limit")) == "llm_provider_transport_error"
    assert classify_llm_phase_exception(RuntimeError("x")) == "unexpected_error"


def test_agent_output_error_default_code() -> None:
    e = AgentOutputError("legacy")
    assert e.code == AgentFailureCode.MODEL_SEMANTIC


def test_classify_schema_invalid_code() -> None:
    assert (
        classify_llm_phase_exception(AgentOutputError("wrap", code=AgentFailureCode.MODEL_SCHEMA))
        == "model_output_schema_invalid"
    )


def test_analysis_agent_terminal_error_when_plan_empty() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="x",
        user_goal_text="g",
    )
    outcome = PlanningOutcome(
        ok=True,
        plan=OrchestrationPlan(steps=[]),
        interpreted_goal=ig,
        errors=[],
    )
    planner = MagicMock()
    planner.build_plan.return_value = outcome
    planner.describe_plan = MagicMock(return_value="")
    agent = AnalysisAgent(planner=planner, executor=MagicMock())
    inp = OrchestrationInput(tickers=["AAPL"], analysis_goal="test", refresh=False)
    out, state = agent.run_returning_state(inp)
    assert state is None
    assert out.status == OrchestrationRunStatus.error
    assert "handoff" in out.message.lower() or "rejected" in out.message.lower()
    assert out.errors and out.errors[0].code == "ORCH_VALIDATION"
