"""Named plan templates: selection and snapshot contracts."""

from __future__ import annotations

from edgar_project.orchestration.goal_preferences import parse_goal_preferences
from edgar_project.orchestration.intent import interpret_goal_intent
from edgar_project.orchestration.plan_templates import (
    build_plan_template_snapshot,
    get_plan_template_snapshot,
    interpreted_goal_code_for,
    select_plan_template,
)
from edgar_project.orchestration.schemas import (
    InterpretedGoalCode,
    OrchestrationIntent,
    PlanTemplateId,
)


def test_registry_each_template_has_run_or_granular_profile() -> None:
    for tid in PlanTemplateId:
        snap = get_plan_template_snapshot(tid)
        assert snap.mcp_execution_profile in ("granular", "run_pipeline")
        assert len(snap.ordered_phases) >= 1
        assert isinstance(snap.peer_analysis_mandatory, bool)


def test_select_anomaly_template_for_plain_outlier_screen() -> None:
    text = "find unusual financial changes"
    prefs = parse_goal_preferences(text)
    interp = interpret_goal_intent(text)
    assert interp is not None
    tid, rules = select_plan_template(prefs, interp)
    assert tid == PlanTemplateId.anomaly_unusual_changes
    assert "select:anomaly_screen_granular" in rules
    assert interpreted_goal_code_for(tid, interp) == InterpretedGoalCode.anomaly_unusual_changes


def test_snapshot_includes_selection_rules() -> None:
    snap = build_plan_template_snapshot(PlanTemplateId.trend_deterioration, ["select:test"])
    assert "select:test" in snap.template_rules_matched
    assert snap.template_id == PlanTemplateId.trend_deterioration


def test_full_pipeline_intent_maps_to_trend_deterioration_template() -> None:
    text = "run the pipeline for these tickers"
    prefs = parse_goal_preferences(text)
    interp = interpret_goal_intent(text)
    assert interp is not None and interp.intent == OrchestrationIntent.full_pipeline_run
    tid, _ = select_plan_template(prefs, interp)
    assert tid == PlanTemplateId.trend_deterioration
