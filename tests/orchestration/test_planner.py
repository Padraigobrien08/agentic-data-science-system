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
    DirectionalFocus,
    InterpretedGoalCode,
    MetricPriority,
    OrchestrationInput,
    OrchestrationIntent,
    PlanTemplateId,
    PreferredSignalStyle,
    PrimaryAnalysisMode,
    TimeFocus,
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
    assert out.interpreted_goal.goal_preferences is not None
    assert out.interpreted_goal.goal_preferences.primary_analysis_mode == PrimaryAnalysisMode.anomaly
    assert out.interpreted_goal.code == InterpretedGoalCode.anomaly_unusual_changes
    assert out.interpreted_goal.plan_template is not None
    assert out.interpreted_goal.plan_template.template_id == PlanTemplateId.anomaly_unusual_changes
    assert out.interpreted_goal.plan_template.mcp_execution_profile == "granular"


def test_peer_report_uses_run_pipeline_single_step() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="build the report for this peer set",
            refresh=True,
        )
    )
    assert out.ok and out.plan
    assert len(out.plan.steps) == 1
    assert out.plan.steps[0].tool_name == TOOL_RUN_PIPELINE
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.intent == OrchestrationIntent.peer_report
    assert out.interpreted_goal.code == InterpretedGoalCode.peer_comparison
    assert out.interpreted_goal.plan_template is not None
    assert out.interpreted_goal.plan_template.template_id == PlanTemplateId.peer_comparison


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
    assert out.routing_source == "deterministic"
    assert out.effective_tickers == ["AAPL"]
    assert len(out.rewrite_suggestions) >= 2
    assert out.errors[0].code == CODE_ORCH_UNSUPPORTED_GOAL


def test_out_of_scope_ticker_returns_scope_guidance() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="Analyze TSLA over the last 8 quarters for margin pressure",
            refresh=False,
        )
    )

    assert not out.ok
    assert out.routing_source == "deterministic"
    assert out.out_of_scope_tickers == ["TSLA"]
    assert out.effective_tickers == ["AAPL", "MSFT"]
    assert any("TSLA" in suggestion for suggestion in out.rewrite_suggestions)
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
    assert out.interpreted_goal.code == InterpretedGoalCode.peer_comparison
    assert out.interpreted_goal.plan_template is not None
    assert out.interpreted_goal.plan_template.peer_analysis_mandatory is True


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
    assert len(d["plan"]["steps"]) == 1
    assert d["plan"]["steps"][0]["tool_name"] == TOOL_RUN_PIPELINE


def test_prompt_named_in_scope_subset_narrows_effective_tickers() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT", "NVDA"],
            analysis_goal="Detect any signs of financial deterioration in MSFT over recent quarters",
            refresh=False,
        )
    )

    assert out.ok and out.plan is not None
    assert len(out.plan.steps) == 1
    assert out.plan.steps[0].tool_name == TOOL_RUN_PIPELINE
    assert out.plan.steps[0].tool_input["tickers"] == ["MSFT"]


def test_multiple_tickers_without_relative_language_do_not_force_peer_report() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal="Analyze AAPL and MSFT over the last 8 quarters for margin pressure",
            refresh=False,
        )
    )

    assert out.ok and out.interpreted_goal is not None
    assert out.interpreted_goal.intent == OrchestrationIntent.anomaly_analysis
    assert out.interpreted_goal.code == InterpretedGoalCode.trend_deterioration


EXAMPLE_DETERIORATION_GOAL = (
    "Detect any signs of financial deterioration in the selected companies over recent quarters. "
    "Focus on declining margins, slowing revenue growth, and weakening cash flow. "
    "Prioritize persistent negative trends rather than one-off anomalies."
)


def test_deterioration_example_prefers_run_pipeline_and_preferences() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(tickers=["AAPL", "MSFT", "NVDA"], analysis_goal=EXAMPLE_DETERIORATION_GOAL, refresh=False)
    )
    assert out.ok and out.plan
    assert len(out.plan.steps) == 1
    assert out.plan.steps[0].tool_name == TOOL_RUN_PIPELINE
    assert out.interpreted_goal is not None
    assert out.interpreted_goal.code == InterpretedGoalCode.trend_deterioration
    assert out.interpreted_goal.plan_template is not None
    assert out.interpreted_goal.plan_template.template_id == PlanTemplateId.trend_deterioration
    assert out.interpreted_goal.plan_template.persistence_filtering_required is True
    gp = out.interpreted_goal.goal_preferences
    assert gp is not None
    assert gp.primary_analysis_mode != PrimaryAnalysisMode.anomaly
    assert gp.preferred_signal_style == PreferredSignalStyle.persistent
    assert gp.directional_focus == DirectionalFocus.negative
    assert MetricPriority.margins in gp.priority_metrics
    assert MetricPriority.revenue_growth in gp.priority_metrics
    assert MetricPriority.cash_flow in gp.priority_metrics
    assert gp.time_focus == TimeFocus.recent_quarters
