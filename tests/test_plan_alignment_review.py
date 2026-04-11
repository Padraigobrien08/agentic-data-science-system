"""Deterministic plan–goal alignment (critic phase, no LLM)."""

from __future__ import annotations

from edgar_project.orchestration.plan_templates import get_plan_template_snapshot
from edgar_project.orchestration.schemas import (
    GoalPreferences,
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationIntent,
    PlanTemplateId,
    PreferredSignalStyle,
    PrimaryAnalysisMode,
)
from edgar_project.mcp.schemas import ARTIFACT_KEY_DETERIORATION_FOCUS

from backend.agents.plan_alignment_review import compute_plan_alignment_findings


def _ig(
    *,
    prefs: GoalPreferences | None,
    template_id: PlanTemplateId,
) -> InterpretedGoal:
    snap = get_plan_template_snapshot(template_id)
    return InterpretedGoal(
        code=InterpretedGoalCode.trend_deterioration,
        intent=OrchestrationIntent.anomaly_analysis,
        intent_rules_matched=["test"],
        description="d",
        user_goal_text="g",
        goal_preferences=prefs,
        plan_template=snap,
    )


def test_deterioration_prefs_with_anomaly_template_is_high_severity() -> None:
    prefs = GoalPreferences(
        primary_analysis_mode=PrimaryAnalysisMode.deterioration,
    )
    ig = _ig(prefs=prefs, template_id=PlanTemplateId.anomaly_unusual_changes)
    rows = compute_plan_alignment_findings(
        ig,
        analysis_goal="",
        artifact_paths={ARTIFACT_KEY_DETERIORATION_FOCUS: "/tmp/x.csv"},
    )
    codes = [r["code"] for r in rows]
    assert "plan_goal_mismatch" in codes
    assert any(r.get("severity") == "high" for r in rows)


def test_persistent_style_anomaly_template_weak_alignment() -> None:
    prefs = GoalPreferences(
        primary_analysis_mode=PrimaryAnalysisMode.anomaly,
        preferred_signal_style=PreferredSignalStyle.persistent,
    )
    ig = _ig(prefs=prefs, template_id=PlanTemplateId.anomaly_unusual_changes)
    rows = compute_plan_alignment_findings(ig, analysis_goal="", artifact_paths={})
    assert any(r["code"] == "weak_alignment_with_persistent_signal_request" for r in rows)


def test_text_fallback_deterioration_vs_anomaly_plan() -> None:
    ig = _ig(prefs=None, template_id=PlanTemplateId.anomaly_unusual_changes)
    rows = compute_plan_alignment_findings(
        ig,
        analysis_goal="show persistent deterioration in margins",
        artifact_paths={},
    )
    assert any(r["code"] == "plan_goal_mismatch" for r in rows)


def test_peer_comparison_prefs_with_non_peer_template_high_severity() -> None:
    prefs = GoalPreferences(primary_analysis_mode=PrimaryAnalysisMode.peer_comparison)
    ig = _ig(prefs=prefs, template_id=PlanTemplateId.anomaly_unusual_changes)
    rows = compute_plan_alignment_findings(ig, analysis_goal="", artifact_paths={})
    codes = [r["code"] for r in rows]
    assert "plan_goal_mismatch" in codes
    assert any(r.get("severity") == "high" for r in rows)
