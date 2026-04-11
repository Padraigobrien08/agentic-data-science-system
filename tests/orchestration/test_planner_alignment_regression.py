"""
Regression anchors for planner ↔ goal-preferences ↔ plan-template alignment.

Uses fixed user-facing ``analysis_goal`` strings; all expectations are deterministic
(no LLM, no network).
"""

from __future__ import annotations

from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import (
    DirectionalFocus,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationIntent,
    PlanTemplateId,
    PreferredSignalStyle,
    PrimaryAnalysisMode,
    TimeFocus,
)

# --- User-request strings (keep in sync with product examples / UI copy) ---

GOAL_DETERIORATION_PERSISTENT_NOT_ONE_OFF = (
    "Detect any signs of financial deterioration in the selected companies over recent quarters. "
    "Prioritize persistent negative trends rather than one-off anomalies."
)

GOAL_ONE_OFF_MARGIN_CASH_ANOMALIES = (
    "Find unusual one-off anomalies in margins and cash flow."
)

GOAL_PEER_UNDERPERFORMERS = (
    "Compare these companies against peers and highlight underperformers."
)

GOAL_MIXED_DETERIORATION_AND_ANOMALIES = "Find persistent deterioration and any unusual anomalies."


def test_regression_deterioration_not_anomaly_only_pipeline() -> None:
    """Persistent / negative / deterioration — not the granular anomaly-only template."""
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT", "NVDA"],
            analysis_goal=GOAL_DETERIORATION_PERSISTENT_NOT_ONE_OFF,
            refresh=False,
        )
    )
    assert out.ok and out.plan and out.interpreted_goal
    ig = out.interpreted_goal
    assert ig.intent == OrchestrationIntent.anomaly_analysis
    assert ig.code == InterpretedGoalCode.trend_deterioration
    assert ig.plan_template is not None
    assert ig.plan_template.template_id == PlanTemplateId.trend_deterioration
    assert ig.plan_template.template_id != PlanTemplateId.anomaly_unusual_changes
    assert ig.plan_template.mcp_execution_profile == "run_pipeline"
    gp = ig.goal_preferences
    assert gp is not None
    assert gp.primary_analysis_mode != PrimaryAnalysisMode.anomaly
    assert gp.preferred_signal_style == PreferredSignalStyle.persistent
    assert gp.directional_focus == DirectionalFocus.negative
    assert gp.time_focus == TimeFocus.recent_quarters


def test_regression_one_off_anomaly_screen_granular() -> None:
    """Explicit one-off + anomaly language → anomaly template, one_off preference."""
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal=GOAL_ONE_OFF_MARGIN_CASH_ANOMALIES,
            refresh=False,
        )
    )
    assert out.ok and out.interpreted_goal
    ig = out.interpreted_goal
    assert ig.intent == OrchestrationIntent.anomaly_analysis
    assert ig.code == InterpretedGoalCode.anomaly_unusual_changes
    assert ig.plan_template is not None
    assert ig.plan_template.template_id == PlanTemplateId.anomaly_unusual_changes
    assert ig.plan_template.mcp_execution_profile == "granular"
    gp = ig.goal_preferences
    assert gp is not None
    assert gp.primary_analysis_mode == PrimaryAnalysisMode.anomaly
    assert gp.preferred_signal_style == PreferredSignalStyle.one_off


def test_regression_peer_comparison_plan() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal=GOAL_PEER_UNDERPERFORMERS,
            refresh=False,
        )
    )
    assert out.ok and out.interpreted_goal
    ig = out.interpreted_goal
    assert ig.intent == OrchestrationIntent.peer_report
    assert ig.code == InterpretedGoalCode.peer_comparison
    assert ig.plan_template is not None
    assert ig.plan_template.template_id == PlanTemplateId.peer_comparison
    assert ig.plan_template.peer_analysis_mandatory is True


def test_regression_mixed_trend_and_anomaly_template() -> None:
    """Competing deterioration + anomaly cues → mixed template (not anomaly-only)."""
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal=GOAL_MIXED_DETERIORATION_AND_ANOMALIES,
            refresh=False,
        )
    )
    assert out.ok and out.interpreted_goal
    ig = out.interpreted_goal
    assert ig.intent == OrchestrationIntent.anomaly_analysis
    assert ig.plan_template is not None
    assert ig.plan_template.template_id == PlanTemplateId.mixed_trend_and_anomaly
    assert ig.plan_template.template_id != PlanTemplateId.anomaly_unusual_changes
    gp = ig.goal_preferences
    assert gp is not None
    # "persistent" in the goal text wins signal-style classification; template still mixes workflows.
    assert gp.preferred_signal_style == PreferredSignalStyle.persistent
    assert gp.time_focus == TimeFocus.mixed
