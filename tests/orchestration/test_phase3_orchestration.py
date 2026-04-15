"""
Phase 3 orchestration integration tests (mocked MCP; no SEC).

Covers planner + executor + agent with ``edgar_project.orchestration.executor.mcp_tools`` patched.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_REPORT,
    ErrorInfo,
    ResolveCompanyInput,
    ToolResponseEnvelope,
    ToolStatus,
)
from edgar_project.orchestration.agent import AnalysisAgent
from edgar_project.orchestration.execution_contract import ExecutionRequest
from edgar_project.orchestration.executor import Executor
from edgar_project.orchestration.planner import (
    TOOL_BUILD_PANEL,
    TOOL_COMPUTE_FEATURES,
    TOOL_DETECT_ANOMALIES,
    TOOL_FETCH_COMPANY_DATA,
    TOOL_GENERATE_REPORT,
    TOOL_RESOLVE_COMPANY,
    TOOL_RUN_PIPELINE,
    Planner,
)
from edgar_project.orchestration.schemas import (
    CODE_ORCH_ALL_RESOLVE_FAILED,
    CODE_ORCH_DISPATCH,
    CODE_ORCH_PARTIAL_RESOLVE,
    CODE_ORCH_RESOLVE_TICKER_FAILED,
    CODE_ORCH_UNSUPPORTED_GOAL,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationIntent,
    OrchestrationOutput,
    OrchestrationRunStatus,
)

# Patch where the executor holds references to tool callables.
_MCP = "edgar_project.orchestration.executor.mcp_tools"


def _ok(
    *,
    message: str = "ok",
    data: dict | None = None,
    artifacts: dict | None = None,
) -> ToolResponseEnvelope:
    return ToolResponseEnvelope(
        status=ToolStatus.success,
        message=message,
        data=data or {},
        artifacts=artifacts or {},
        errors=[],
    )


def _err(code: str, message: str) -> ToolResponseEnvelope:
    return ToolResponseEnvelope(
        status=ToolStatus.error,
        message=message,
        data={},
        artifacts={},
        errors=[ErrorInfo(code=code, message=message)],
    )


def _no_data(message: str = "no data") -> ToolResponseEnvelope:
    return ToolResponseEnvelope(
        status=ToolStatus.no_data,
        message=message,
        data={},
        artifacts={},
        errors=[],
    )


def _granular_mocks_two_tickers() -> dict[str, MagicMock]:
    """Happy path: two symbols through resolve → report."""

    def resolve(inp: ResolveCompanyInput):
        cik = {"AAPL": 320193, "MSFT": 789019}[inp.ticker]
        return _ok(data={"ticker": inp.ticker, "cik": cik, "company_name": f"Co-{inp.ticker}"})

    def fetch(inp):
        return _ok(data={"ticker": inp.ticker})

    def build_panel(inp):
        return _ok(
            data={"row_count": 4, "ciks": [320193, 789019]},
            artifacts={ARTIFACT_KEY_PANEL: "/tmp/mock/panel.csv"},
        )

    def compute_features(inp):
        return _ok(
            data={"row_count": 4},
            artifacts={ARTIFACT_KEY_FEATURES: "/tmp/mock/features.csv"},
        )

    def detect(inp):
        return _ok(
            data={"feature_row_count": 4, "anomaly_count": 2},
            artifacts={ARTIFACT_KEY_ANOMALIES: "/tmp/mock/anomalies.csv"},
        )

    def report(inp):
        return _ok(
            data={"report_chars": 1200, "report": {"path": "/tmp/mock/report.md"}},
            artifacts={ARTIFACT_KEY_REPORT: "/tmp/mock/report.md"},
        )

    return {
        "resolve_company_tool": MagicMock(side_effect=resolve),
        "fetch_company_data_tool": MagicMock(side_effect=fetch),
        "build_panel_tool": MagicMock(side_effect=build_panel),
        "compute_features_tool": MagicMock(side_effect=compute_features),
        "detect_anomalies_tool": MagicMock(side_effect=detect),
        "generate_report_tool": MagicMock(side_effect=report),
    }


def _assert_core_output_shape(out: OrchestrationOutput) -> None:
    assert isinstance(out.run_id, str) and len(out.run_id) >= 8
    assert isinstance(out.status, OrchestrationRunStatus)
    assert out.message
    assert out.interpreted_goal.user_goal_text
    assert isinstance(out.tool_call_sequence, list)
    assert isinstance(out.tool_results_summary, list)
    assert isinstance(out.step_statuses, list)
    assert isinstance(out.artifact_paths, dict)
    assert isinstance(out.errors, list)
    assert isinstance(out.warnings, list)
    assert out.interpreted_goal.intent is not None or out.status == OrchestrationRunStatus.error


@patch.multiple(_MCP, **_granular_mocks_two_tickers())
def test_successful_full_granular_pipeline() -> None:
    """1. End-to-end granular path: all MCP steps succeed."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.status == OrchestrationRunStatus.success
    assert out.errors == []
    assert out.interpreted_goal.intent == OrchestrationIntent.anomaly_analysis
    assert out.final_report_path == "/tmp/mock/report.md"
    assert ARTIFACT_KEY_PANEL in out.artifact_paths
    assert ARTIFACT_KEY_FEATURES in out.artifact_paths
    assert ARTIFACT_KEY_ANOMALIES in out.artifact_paths
    assert ARTIFACT_KEY_REPORT in out.artifact_paths
    names = [s.tool_name for s in out.step_statuses]
    labels = [s.label for s in out.step_statuses]
    assert names[-1] == TOOL_GENERATE_REPORT
    assert labels[-1] == f"{TOOL_GENERATE_REPORT}:explicit_paths"
    assert out.tool_call_sequence[-1].params["use_default_artifact_paths"] is False
    assert all(s.mcp_status == "success" for s in out.step_statuses)
    _assert_core_output_shape(out)


@patch.multiple(
    _MCP,
    resolve_company_tool=MagicMock(
        side_effect=lambda inp: _ok(data={"ticker": inp.ticker, "cik": 1, "company_name": "A"})
        if inp.ticker == "AAPL"
        else _err("UNKNOWN_TICKER", f"bad {inp.ticker}")
    ),
    fetch_company_data_tool=MagicMock(side_effect=lambda inp: _ok(data={"ticker": inp.ticker})),
    build_panel_tool=MagicMock(
        side_effect=lambda inp: _ok(
            data={"row_count": 2, "ciks": [1]},
            artifacts={ARTIFACT_KEY_PANEL: "/tmp/panel.csv"},
        )
    ),
    compute_features_tool=MagicMock(
        side_effect=lambda inp: _ok(data={"row_count": 2}, artifacts={ARTIFACT_KEY_FEATURES: "/tmp/f.csv"})
    ),
    detect_anomalies_tool=MagicMock(
        side_effect=lambda inp: _ok(
            data={"feature_row_count": 2, "anomaly_count": 1},
            artifacts={ARTIFACT_KEY_ANOMALIES: "/tmp/a.csv"},
        )
    ),
    generate_report_tool=MagicMock(
        side_effect=lambda inp: _ok(
            data={"report_chars": 100, "report": {"path": "/tmp/r.md"}},
            artifacts={ARTIFACT_KEY_REPORT: "/tmp/r.md"},
        )
    ),
)
def test_partial_success_one_ticker_resolve_fails() -> None:
    """2. One resolve fails; run continues; partial_success and warnings."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["AAPL", "BAD"],
            analysis_goal="detect anomalies in financials",
            refresh=False,
        )
    )
    assert out.status == OrchestrationRunStatus.partial_success
    codes = {w.code for w in out.warnings}
    assert CODE_ORCH_PARTIAL_RESOLVE in codes or CODE_ORCH_RESOLVE_TICKER_FAILED in codes
    assert out.errors == []
    assert ARTIFACT_KEY_PANEL in out.artifact_paths


@patch.multiple(
    _MCP,
    resolve_company_tool=MagicMock(
        side_effect=lambda inp: _ok(data={"ticker": inp.ticker, "cik": 999, "company_name": "X"})
    ),
    fetch_company_data_tool=MagicMock(side_effect=lambda inp: _no_data("empty cache")),
    build_panel_tool=MagicMock(side_effect=lambda inp: _ok(data={"row_count": 0})),
)
def test_no_data_all_fetches_skip_build_panel() -> None:
    """3. All fetches no_data → orchestration no_data; build_panel not invoked."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.status == OrchestrationRunStatus.no_data
    assert not any(s.tool_name == TOOL_BUILD_PANEL for s in out.tool_results_summary)
    assert all(s.tool_name != TOOL_BUILD_PANEL for s in out.tool_call_sequence)


@patch.multiple(
    _MCP,
    resolve_company_tool=MagicMock(side_effect=lambda inp: _err("X", "fail")),
    fetch_company_data_tool=MagicMock(),
    build_panel_tool=MagicMock(),
)
def test_hard_error_all_resolve_fail() -> None:
    """4a. Every resolve fails → error + fatal code; no downstream tools."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["A", "B"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.status == OrchestrationRunStatus.error
    assert any(e.code == CODE_ORCH_ALL_RESOLVE_FAILED for e in out.errors)
    assert len(out.tool_results_summary) == 2
    assert all(s.tool_name == TOOL_RESOLVE_COMPANY for s in out.tool_results_summary)


@patch.multiple(
    _MCP,
    run_pipeline_tool=MagicMock(
        side_effect=lambda inp: _err("PIPE_FAIL", "pipeline internal error"),
    ),
)
def test_hard_error_run_pipeline_propagates() -> None:
    """4b. Single-step pipeline MCP error → orchestration error."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="run the pipeline for these tickers",
            refresh=False,
        )
    )
    assert out.status == OrchestrationRunStatus.error
    assert out.errors
    assert out.errors[0].mcp_error_code == "PIPE_FAIL"


def test_planner_deterministic_supported_goals() -> None:
    """5. Same goal + tickers → identical tool sequence and intent."""
    p = Planner()
    req = OrchestrationInput(tickers=["AAPL", "MSFT"], analysis_goal="compare peers and write a report", refresh=False)
    a = p.build_plan(req)
    b = p.build_plan(req)
    assert a.ok and b.ok
    assert a.interpreted_goal is not None and b.interpreted_goal is not None
    assert a.interpreted_goal.intent == b.interpreted_goal.intent == OrchestrationIntent.peer_report
    assert a.interpreted_goal.code == InterpretedGoalCode.peer_comparison
    assert [s.tool_name for s in sorted(a.plan.steps, key=lambda x: x.order)] == [
        s.tool_name for s in sorted(b.plan.steps, key=lambda x: x.order)
    ]
    names = [s.tool_name for s in sorted(a.plan.steps, key=lambda x: x.order)]
    assert names == [TOOL_RUN_PIPELINE]


def test_planner_uses_explicit_report_paths_for_granular_plan() -> None:
    out = Planner().build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.ok and out.plan is not None
    report_step = [s for s in out.plan.steps if s.tool_name == TOOL_GENERATE_REPORT][-1]
    assert report_step.label == f"{TOOL_GENERATE_REPORT}:explicit_paths"
    assert report_step.tool_input["use_default_artifact_paths"] is False
    assert report_step.tool_input["features_csv_path"] is None
    assert report_step.tool_input["anomalies_csv_path"] is None


@pytest.mark.parametrize(
    ("goal", "intent", "head_tool"),
    [
        ("find unusual financial changes", OrchestrationIntent.anomaly_analysis, TOOL_RESOLVE_COMPANY),
        ("run the pipeline for these tickers", OrchestrationIntent.full_pipeline_run, TOOL_RUN_PIPELINE),
        ("compare companies and generate a report", OrchestrationIntent.peer_report, TOOL_RUN_PIPELINE),
    ],
)
def test_planner_intent_and_first_tool(goal: str, intent: OrchestrationIntent, head_tool: str) -> None:
    out = Planner().build_plan(OrchestrationInput(tickers=["AAPL"], analysis_goal=goal, refresh=False))
    assert out.ok and out.plan
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.intent == intent
    first = min(out.plan.steps, key=lambda s: s.order)
    assert first.tool_name == head_tool


@patch.multiple(_MCP, **_granular_mocks_two_tickers())
def test_final_response_shape_and_status_enum() -> None:
    """6. OrchestrationOutput fields and status values are stable."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="outlier detection report",
            refresh=False,
        )
    )
    _assert_core_output_shape(out)
    assert out.status in OrchestrationRunStatus
    dumped = out.model_dump(mode="json")
    assert dumped["status"] == "success"
    assert dumped["interpreted_goal"]["intent"] == "anomaly_analysis"
    assert len(dumped["step_statuses"]) == len(dumped["tool_results_summary"])


@patch.multiple(
    _MCP,
    resolve_company_tool=MagicMock(
        side_effect=lambda inp: _ok(data={"ticker": inp.ticker, "cik": 1, "company_name": "C"})
    ),
    fetch_company_data_tool=MagicMock(side_effect=lambda inp: _ok()),
    build_panel_tool=MagicMock(
        side_effect=lambda inp: _ok(
            data={"row_count": 1},
            artifacts={ARTIFACT_KEY_PANEL: "/keep/panel.csv"},
        )
    ),
    compute_features_tool=MagicMock(
        side_effect=lambda inp: _ok(
            data={"row_count": 1},
            artifacts={ARTIFACT_KEY_FEATURES: "/keep/features.csv"},
        )
    ),
    detect_anomalies_tool=MagicMock(
        side_effect=lambda inp: _ok(
            data={"feature_row_count": 1, "anomaly_count": 1},
            artifacts={ARTIFACT_KEY_ANOMALIES: "/keep/anomalies.csv"},
        )
    ),
    generate_report_tool=MagicMock(side_effect=lambda inp: _err("REPORT_GEN", "writer failed")),
)
def test_artifacts_preserved_on_late_report_failure() -> None:
    """7. Report step fails; prior artifact paths remain; partial_success."""
    out = AnalysisAgent().run(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="find unusual financial changes",
            refresh=False,
        )
    )
    assert out.status == OrchestrationRunStatus.partial_success
    assert out.artifact_paths.get(ARTIFACT_KEY_PANEL) == "/keep/panel.csv"
    assert out.artifact_paths.get(ARTIFACT_KEY_FEATURES) == "/keep/features.csv"
    assert out.artifact_paths.get(ARTIFACT_KEY_ANOMALIES) == "/keep/anomalies.csv"
    assert ARTIFACT_KEY_REPORT not in out.artifact_paths
    assert out.errors
    assert out.errors[0].code == "REPORT_GEN"


@patch(_MCP + ".resolve_company_tool", side_effect=RuntimeError("dispatch boom"))
def test_dispatch_exception_surfaces_as_error(mock_resolve: MagicMock) -> None:
    """Hard failure: MCP dispatch raises → error outcome, no silent pass."""
    request = OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)
    planner = Planner()
    outcome = planner.build_plan(request)
    assert outcome.ok
    execution = ExecutionRequest.from_planning(run_id="00000000-0000-0000-0000-000000000001", request=request, outcome=outcome)
    out = Executor().run(execution)
    assert out.status == OrchestrationRunStatus.error
    assert any(e.code == CODE_ORCH_DISPATCH for e in out.errors)
    assert mock_resolve.call_count >= 1


def test_unsupported_goal_validation_without_mcp() -> None:
    """Planner rejects unknown phrasing before any executor / MCP."""
    out = Planner().build_plan(
        OrchestrationInput(tickers=["AAPL"], analysis_goal="totally vague nonsense xyz", refresh=False)
    )
    assert not out.ok
    assert out.errors[0].code == CODE_ORCH_UNSUPPORTED_GOAL
