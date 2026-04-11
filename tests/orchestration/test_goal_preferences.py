"""Rule-based :class:`GoalPreferences` parsing (no MCP)."""

from __future__ import annotations

from edgar_project.orchestration.goal_preferences import parse_goal_preferences, prefer_run_pipeline_over_granular
from edgar_project.orchestration.schemas import (
    DirectionalFocus,
    MetricPriority,
    PeerRequirement,
    PreferredSignalStyle,
    PrimaryAnalysisMode,
    TimeFocus,
)


def test_parse_deterioration_persistent_metrics() -> None:
    goal = (
        "Detect any signs of financial deterioration in the selected companies over recent quarters. "
        "Focus on declining margins, slowing revenue growth, and weakening cash flow. "
        "Prioritize persistent negative trends rather than one-off anomalies."
    )
    gp = parse_goal_preferences(goal)
    assert gp.primary_analysis_mode == PrimaryAnalysisMode.deterioration
    assert gp.preferred_signal_style == PreferredSignalStyle.persistent
    assert gp.directional_focus == DirectionalFocus.negative
    assert gp.priority_metrics[:3] == [
        MetricPriority.margins,
        MetricPriority.revenue_growth,
        MetricPriority.cash_flow,
    ]
    assert gp.time_focus == TimeFocus.recent_quarters
    assert gp.peer_requirement == PeerRequirement.none
    assert prefer_run_pipeline_over_granular(gp) is True


def test_parse_plain_anomaly_screen_prefers_granular() -> None:
    gp = parse_goal_preferences("find unusual financial changes and z-score outliers")
    assert gp.primary_analysis_mode == PrimaryAnalysisMode.anomaly
    assert prefer_run_pipeline_over_granular(gp) is False


def test_parse_trend_keyword() -> None:
    gp = parse_goal_preferences("focus on revenue trends over the last 8 quarters")
    assert gp.primary_analysis_mode == PrimaryAnalysisMode.trend
    assert prefer_run_pipeline_over_granular(gp) is True


def test_peer_optional_triggers_pipeline_when_peer_keyword() -> None:
    gp = parse_goal_preferences("compare margins vs industry peers")
    assert gp.primary_analysis_mode == PrimaryAnalysisMode.peer_comparison
    assert gp.peer_requirement == PeerRequirement.optional
    assert prefer_run_pipeline_over_granular(gp) is True


def test_bare_compare_does_not_force_peer_primary_mode() -> None:
    """Regression: 'compare' alone is not a peer signal (avoid coupling to intent keywords)."""
    gp = parse_goal_preferences("Compare Q1 revenue to Q2 year over year for each ticker")
    assert gp.primary_analysis_mode != PrimaryAnalysisMode.peer_comparison
    assert gp.peer_requirement == PeerRequirement.none
