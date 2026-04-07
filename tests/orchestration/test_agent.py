"""Top-level agent entry (no MCP)."""

from __future__ import annotations

from edgar_project.orchestration import (
    CODE_ORCH_VALIDATION,
    InterpretedGoalCode,
    OrchestrationRunStatus,
    run_analysis_agent,
)


def test_run_analysis_agent_dict_input_planning_error() -> None:
    out = run_analysis_agent(
        {
            "tickers": ["A", "B", "C", "D", "E", "F"],
            "analysis_goal": "test",
        }
    )
    assert out.status == OrchestrationRunStatus.error
    assert out.errors
    assert out.errors[0].code == CODE_ORCH_VALIDATION
    assert out.interpreted_goal.code == InterpretedGoalCode.planning_failed
    assert out.interpreted_goal.intent is None
    assert "steps:" in out.final_summary
    assert out.tool_call_sequence == []


