"""Deterministic planner behavior (no MCP, no network)."""

from __future__ import annotations

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
    CODE_ORCH_UNSUPPORTED_GOAL,
    CODE_ORCH_VALIDATION,
    OrchestrationIntent,
    OrchestrationInput,
)


def test_granular_path_keyword_anomaly() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="find unusual financial changes and anomalies",
            refresh=False,
        )
    )
    assert out.ok
    assert out.plan is not None
    names = [s.tool_name for s in sorted(out.plan.steps, key=lambda x: x.order)]
    assert names == [
        TOOL_RESOLVE_COMPANY,
        TOOL_FETCH_COMPANY_DATA,
        TOOL_BUILD_PANEL,
        TOOL_COMPUTE_FEATURES,
        TOOL_DETECT_ANOMALIES,
        TOOL_GENERATE_REPORT,
    ]
    assert out.plan.steps[0].tool_input == {"ticker": "AAPL"}
    assert out.plan.steps[1].tool_input == {"ticker": "AAPL", "refresh": False}
    assert "resolve_company:AAPL" in p.describe_outcome(out)
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.intent == OrchestrationIntent.anomaly_analysis
    assert out.interpreted_goal.intent_rules_matched


def test_granular_path_two_tickers_order_and_labels() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="build the report for this peer set",
            refresh=True,
        )
    )
    assert out.ok and out.plan
    assert len(out.plan.steps) == 2 + 2 + 4  # resolve×2 fetch×2 + 4 tail
    labels = [s.label for s in out.plan.steps]
    assert "resolve_company:AAPL" in labels
    assert "fetch_company_data:MSFT" in labels
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.intent == OrchestrationIntent.peer_report


def test_full_pipeline_intent_run_pipeline_single_step() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="run the pipeline for these tickers",
            refresh=False,
        )
    )
    assert out.ok
    assert out.plan is not None
    assert len(out.plan.steps) == 1
    assert out.plan.steps[0].tool_name == TOOL_RUN_PIPELINE
    assert out.plan.steps[0].tool_input["tickers"] == ["AAPL"]
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.intent == OrchestrationIntent.full_pipeline_run


def test_unsupported_goal_returns_error() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="do something unspecified",
            refresh=False,
        )
    )
    assert not out.ok
    assert out.errors[0].code == CODE_ORCH_UNSUPPORTED_GOAL


def test_compare_companies_report_peer_intent() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="compare these companies and generate a report",
            refresh=False,
        )
    )
    assert out.ok
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.intent == OrchestrationIntent.peer_report


def test_too_many_tickers_validation() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["A", "B", "C", "D", "E", "F"],
            analysis_goal="anomaly report",
            refresh=False,
        )
    )
    assert not out.ok
    assert out.errors[0].code == CODE_ORCH_VALIDATION


def test_planning_outcome_json_round_trip() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(tickers=["NVDA"], analysis_goal="trend analysis report", refresh=False)
    )
    assert out.ok
    d = out.model_dump(mode="json")
    assert d["ok"] is True
    assert len(d["plan"]["steps"]) == 6
