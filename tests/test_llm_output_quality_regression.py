"""
Regression anchors for LLM-layer *quality* contracts (no live OpenAI calls).

These tests load **frozen JSON fixtures** that mimic ideal model outputs, then assert:

1. Intent JSON still maps to coherent :class:`~edgar_project.orchestration.schemas.InterpretedGoal` rows.
2. Planning JSON still validates, orders steps, and passes executor handoff checks.
3. Critic JSON still carries the narrative + issues fields prompts rely on.
4. Report JSON still contains markdown shaped like the report prompt (title, Evidence vs Limitations).
5. Context builders still emit explicit truncation metadata under tight budgets.
6. Per-phase model routing remains a deterministic function of settings (see also ``tests/test_model_routing.py``).

Deterministic planner ↔ template selection is covered separately in
``tests/orchestration/test_planner_alignment_regression.py`` (no LLM fixtures).
"""

from __future__ import annotations

import json
from pathlib import Path

from backend.agents.context_budget import ContextBudget
from backend.agents.llm_context import build_tool_scope_summary, slim_interpreted_goal_for_llm
from backend.agents.llm_plan_handoff import validate_llm_planned_steps_for_handoff
from backend.agents.model_routing import resolve_agent_completion_model
from backend.agents.output_schemas import (
    CriticAgentLLMOutput,
    IntentAgentLLMOutput,
    PlanningAgentLLMOutput,
    ReportAgentLLMOutput,
)
from backend.config.settings import Settings
from edgar_project.orchestration.plan_templates import PlanTemplateId, build_plan_template_snapshot
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationIntent,
    StepStatusEntry,
)

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "llm_regression"


def _load_json(name: str) -> dict:
    path = _FIXTURES / name
    assert path.is_file(), f"missing fixture {path}"
    return json.loads(path.read_text(encoding="utf-8"))


# --- 1. Intent: representative prompts → stable interpretation quality ---


def test_regression_intent_fixture_peer_comparison_maps_correctly() -> None:
    raw = _load_json("intent_peer_comparison.json")
    parsed = IntentAgentLLMOutput.model_validate(raw)
    ig = parsed.to_interpreted_goal()
    assert ig.code == InterpretedGoalCode.peer_comparison
    assert ig.intent == OrchestrationIntent.peer_report
    assert len(ig.description) >= 20
    assert "peer" in ig.user_goal_text.lower()
    assert "regression_fixture_peer_v1" in ig.intent_rules_matched


def test_regression_intent_fixture_trend_deterioration_maps_correctly() -> None:
    raw = _load_json("intent_trend_deterioration.json")
    parsed = IntentAgentLLMOutput.model_validate(raw)
    ig = parsed.to_interpreted_goal()
    assert ig.code == InterpretedGoalCode.trend_deterioration
    assert ig.intent == OrchestrationIntent.anomaly_analysis
    assert "persistent" in ig.user_goal_text.lower() or "deterioration" in ig.user_goal_text.lower()


# --- 2. Planning: allowlist + ordering (pairing with deterministic templates is elsewhere) ---


def test_regression_planning_fixture_validates_and_handoffs() -> None:
    raw = _load_json("planning_run_pipeline.json")
    parsed = PlanningAgentLLMOutput.model_validate(raw)
    steps = parsed.to_planned_steps()
    validate_llm_planned_steps_for_handoff(steps)
    assert [s.order for s in steps] == [0, 1]
    assert steps[-1].tool_name == "run_pipeline"


def test_regression_peer_intent_and_planning_fixtures_are_pipeline_consistent() -> None:
    """LLM intent (peer) should not contradict a minimal executable plan that includes run_pipeline."""
    ig = IntentAgentLLMOutput.model_validate(_load_json("intent_peer_comparison.json")).to_interpreted_goal()
    steps = PlanningAgentLLMOutput.model_validate(_load_json("planning_run_pipeline.json")).to_planned_steps()
    assert ig.code == InterpretedGoalCode.peer_comparison
    assert any(s.tool_name == "run_pipeline" for s in steps)


# --- 3. Critic: caveats / alignment-style issues remain present ---


def test_regression_critic_fixture_preserves_assessment_and_issues() -> None:
    raw = _load_json("critic_with_caveats.json")
    c = CriticAgentLLMOutput.model_validate(raw)
    assert len(c.findings_assessment) >= 40
    assert len(c.caveat_coverage) >= 40
    assert len(c.trustworthiness_notes) >= 30
    assert len(c.issues) >= 2
    assert all("alignment" in issue.lower() or "z-score" in issue.lower() for issue in c.issues)
    assert c.overall_confidence in ("high", "medium", "low")


# --- 4. Report: evidence-oriented structure (matches report prompt constraints) ---


def test_regression_report_fixture_has_title_evidence_and_limitations() -> None:
    raw = _load_json("report_with_evidence_anchors.json")
    r = ReportAgentLLMOutput.model_validate(raw)
    md = r.user_report_markdown.strip()
    assert md.startswith("# ")
    lowered = md.lower()
    assert "## evidence" in lowered
    assert "## limitations" in lowered
    # Prompt asks to anchor in summarized roles / concrete metrics
    assert "findings" in lowered or "panel" in lowered
    assert len(r.key_takeaways) >= 2
    assert all(len(t.strip()) >= 20 for t in r.key_takeaways)
    assert len(r.narrative_thesis.strip()) >= 20
    assert len(r.narrative_whats_happening.strip()) >= 20
    assert len(r.narrative_why_we_think_that.strip()) >= 20
    assert len(r.narrative_what_weakens_claim.strip()) >= 20


# --- 5. Context builders: budgets + truncation metadata ---


def test_regression_slim_goal_truncates_template_rules_with_metadata() -> None:
    many_rules = [f"synthetic_rule_{i:03d}" for i in range(30)]
    snap = build_plan_template_snapshot(PlanTemplateId.peer_comparison, many_rules)
    ig = InterpretedGoal(
        code=InterpretedGoalCode.peer_comparison,
        intent=OrchestrationIntent.peer_report,
        intent_rules_matched=["a", "b"],
        description="d",
        user_goal_text="goal",
        plan_template=snap,
    )
    b = ContextBudget(max_template_rules_matched=4)
    slim, _trunc_meta = slim_interpreted_goal_for_llm(ig, b)
    pt = slim.get("plan_template") or {}
    tr = pt.get("template_rules_matched") or []
    assert len(tr) == 4
    assert tr == sorted(many_rules)[:4]


def test_regression_tool_scope_summary_emits_truncation_sentinel() -> None:
    steps = [
        StepStatusEntry(order=i, tool_name="resolve_company", mcp_status="success")
        for i in range(5)
    ]
    b = ContextBudget(max_step_rows=2)
    scope = build_tool_scope_summary(step_statuses=steps, tool_results_summary=[], budget=b)
    assert scope["step_count"] == 5
    assert any(
        isinstance(x, dict) and x.get("truncated") is True and x.get("omitted_count") == 3
        for x in scope["steps"]
    )


# --- 6. Model routing matrix (frozen expectations; complements tests/test_model_routing.py) ---


def test_regression_model_routing_matrix_for_all_phases() -> None:
    s = Settings(
        agent_completion_model="base-model",
        agent_intent_model="intent-model",
        agent_intent_preferences_model="pref-model",
        agent_planning_model="plan-model",
        agent_critic_model="critic-model",
        agent_report_model="report-model",
    )
    expected: dict[str, tuple[str, str]] = {
        "intent": ("intent-model", "agent_intent_model"),
        "intent_preferences": ("pref-model", "agent_intent_preferences_model"),
        "planning": ("plan-model", "agent_planning_model"),
        "critic": ("critic-model", "agent_critic_model"),
        "report": ("report-model", "agent_report_model"),
    }
    for phase, (model, src) in expected.items():
        assert resolve_agent_completion_model(s, phase) == (model, src)
