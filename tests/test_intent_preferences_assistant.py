"""Optional LLM-assisted goal preferences merge (deterministic planner still selects template)."""

from __future__ import annotations

from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import (
    GoalPreferences,
    IntentAssistancePayload,
    OrchestrationInput,
    PrimaryAnalysisMode,
    PlanTemplateId,
)
from edgar_project.orchestration.goal_preferences import parse_goal_preferences

from backend.agents.intent_preferences_assistant import merge_goal_preferences
from backend.agents.output_schemas import LLMGoalPreferencesPatch


def test_merge_goal_preferences_overlays_patch() -> None:
    base = parse_goal_preferences("find unusual financial changes")
    patch = LLMGoalPreferencesPatch(primary_analysis_mode=PrimaryAnalysisMode.deterioration)
    merged = merge_goal_preferences(base, patch)
    assert merged.primary_analysis_mode == PrimaryAnalysisMode.deterioration
    assert "llm_goal_preferences_patch" in merged.preference_rules_matched


def test_planner_prefers_intent_assistance_over_rule_parse() -> None:
    """Same surface goal text; assistance forces deterioration template path."""
    baseline = Planner().build_plan(
        OrchestrationInput(tickers=["AAPL"], analysis_goal="find unusual financial changes", refresh=False)
    )
    assert baseline.ok and baseline.interpreted_goal and baseline.interpreted_goal.plan_template
    assert baseline.interpreted_goal.plan_template.template_id == PlanTemplateId.anomaly_unusual_changes

    assisted = GoalPreferences(
        primary_analysis_mode=PrimaryAnalysisMode.deterioration,
        preference_rules_matched=["llm_goal_preferences_patch"],
    )
    payload = IntentAssistancePayload(
        goal_preferences=assisted,
        model_call_id="00000000-0000-0000-0000-000000000001",
        prompt_id="edgar.agent.intent_preferences_assistant",
        prompt_version="1.1.0",
    )
    req = OrchestrationInput(
        tickers=["AAPL"],
        analysis_goal="find unusual financial changes",
        refresh=False,
        intent_assistance=payload,
    )
    out = Planner().build_plan(req)
    assert out.ok and out.interpreted_goal and out.interpreted_goal.plan_template
    assert out.interpreted_goal.plan_template.template_id == PlanTemplateId.trend_deterioration
