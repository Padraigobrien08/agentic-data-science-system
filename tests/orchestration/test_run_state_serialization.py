"""OrchestrationRunState JSON contract (no live MCP / SEC)."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from edgar_project.orchestration.constants import ORCH_RUN_STATE_CONTRACT_VERSION, TOOL_RESOLVE_COMPANY
from edgar_project.orchestration.schemas import (
    OrchestrationInput,
    OrchestrationPlan,
    PlannedStep,
    StepRecord,
)
from edgar_project.orchestration.state import OrchestrationRunState


def _minimal_request() -> OrchestrationInput:
    return OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)


def test_run_state_defaults_contract_version() -> None:
    st = OrchestrationRunState(request=_minimal_request())
    assert st.contract_version == ORCH_RUN_STATE_CONTRACT_VERSION


def test_run_state_model_dump_json_round_trip() -> None:
    plan = OrchestrationPlan(
        steps=[
            PlannedStep(
                order=0,
                tool_name=TOOL_RESOLVE_COMPANY,
                tool_input={"ticker": "AAPL"},
                label=f"{TOOL_RESOLVE_COMPANY}:AAPL",
            )
        ]
    )
    st = OrchestrationRunState(
        request=_minimal_request(),
        plan=plan,
        context={"scratch": {"n": 1}, "tags": ["a"]},
    )
    payload = st.model_dump(mode="json")
    raw = json.dumps(payload)
    st2 = OrchestrationRunState.model_validate_json(raw)
    assert st2.request.analysis_goal == st.request.analysis_goal
    assert st2.plan is not None and len(st2.plan.steps) == 1
    assert st2.context == {"scratch": {"n": 1}, "tags": ["a"]}
    assert st2.contract_version == ORCH_RUN_STATE_CONTRACT_VERSION


def test_step_cursor_normalized_after_deserialize_mismatch() -> None:
    st = OrchestrationRunState(
        request=_minimal_request(),
        steps_completed=[
            StepRecord(
                tool_name=TOOL_RESOLVE_COMPANY,
                order=0,
                envelope={"status": "success", "data": {"ticker": "AAPL", "cik": 320193}},
            )
        ],
        current_step_index=0,
    )
    assert st.current_step_index == 1
    dumped = st.model_dump(mode="json")
    dumped["current_step_index"] = 99
    st2 = OrchestrationRunState.model_validate(dumped)
    assert st2.current_step_index == len(st2.steps_completed) == 1


def test_context_rejects_opaque_objects() -> None:
    with pytest.raises(ValidationError):
        OrchestrationRunState.model_validate(
            {
                "request": _minimal_request().model_dump(mode="json"),
                "context": {"bad": object()},
            }
        )
