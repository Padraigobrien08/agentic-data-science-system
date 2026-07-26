"""Planner → executor :class:`ExecutionRequest` contract (no MCP)."""

from __future__ import annotations

import json

import pytest

from edgar_project.orchestration.constants import ORCH_RUN_STATE_CONTRACT_VERSION
from edgar_project.orchestration.execution_contract import ExecutionRequest, ExecutionResult
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import (
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationRunStatus,
    PlanningOutcome,
)
from edgar_project.orchestration.state import OrchestrationRunState


def _request() -> OrchestrationInput:
    return OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)


def test_from_planning_rejects_failed_outcome() -> None:
    bad = PlanningOutcome(ok=False, plan=None, interpreted_goal=None, errors=[])
    with pytest.raises(ValueError, match="non-null plan"):
        ExecutionRequest.from_planning(run_id="r1", request=_request(), outcome=bad)


def test_from_planning_maps_to_run_state() -> None:
    outcome = Planner().build_plan(_request())
    assert outcome.ok and outcome.plan is not None
    ex = ExecutionRequest.from_planning(run_id="run-xyz", request=_request(), outcome=outcome)
    st = ex.to_run_state()
    assert st.run_id == "run-xyz"
    assert st.plan == outcome.plan
    assert st.interpreted_goal == outcome.interpreted_goal
    assert st.contract_version == ORCH_RUN_STATE_CONTRACT_VERSION


def test_execution_request_json_round_trip() -> None:
    outcome = Planner().build_plan(_request())
    assert outcome.ok
    ex = ExecutionRequest.from_planning(run_id="run-json", request=_request(), outcome=outcome)
    raw = json.dumps(ex.model_dump(mode="json"))
    ex2 = ExecutionRequest.model_validate_json(raw)
    assert ex2 == ex
    assert isinstance(ex2.to_run_state(), OrchestrationRunState)


def test_execution_result_is_orchestration_output() -> None:
    assert ExecutionResult is OrchestrationOutput
    outcome = Planner().build_plan(_request())
    assert outcome.ok and outcome.interpreted_goal is not None
    out = OrchestrationOutput(
        run_id="r",
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=outcome.interpreted_goal,
    )
    assert isinstance(out, ExecutionResult)
