"""Compact ``phase_output`` builders for agent / orchestration persistence."""

from __future__ import annotations

from backend.agents.output_schemas import CriticAgentLLMOutput, ReportAgentLLMOutput
from backend.agents.phase_outputs import (
    build_critic_phase_output,
    build_intent_phase_output,
    build_planning_phase_output,
    build_planning_phase_output_from_step_statuses,
    build_report_phase_output,
)
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationIntent,
    OrchestrationPlan,
    PlannedStep,
    StepStatusEntry,
)


def test_intent_phase_output_deterministic() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        intent=OrchestrationIntent.full_pipeline_run,
        intent_rules_matched=["rule:a"],
        description="End-to-end",
        user_goal_text="run it all",
    )
    out = build_intent_phase_output(
        interpreted_goal=ig,
        tickers=["AAPL"],
        analysis_goal="run it all",
        source="deterministic_rules",
    )
    assert out["goal_code"] == "full_pipeline"
    assert out["orchestration_intent"] == "full_pipeline_run"
    assert out["entities"]["tickers"] == ["AAPL"]
    assert out["contract_version"] == "1"
    assert out["planning_transparency"]["present"] is True
    assert out["planning_transparency"]["goal_code"] == "full_pipeline"


def test_planning_phase_output() -> None:
    plan = OrchestrationPlan(
        steps=[
            PlannedStep(order=0, tool_name="resolve_company", tool_input={"ticker": "X"}, label="r"),
        ]
    )
    ig = InterpretedGoal(
        code=InterpretedGoalCode.resolve_only,
        description="x",
        user_goal_text="y",
    )
    out = build_planning_phase_output(plan=plan, interpreted_goal=ig, source="deterministic_rules")
    assert out["step_count"] == 1
    assert out["ordered_plan"][0]["tool_name"] == "resolve_company"
    assert out["chosen_path"]["goal_code"] == "resolve_only"


def test_planning_from_step_statuses() -> None:
    ig = InterpretedGoal(
        code=InterpretedGoalCode.full_pipeline,
        description="d",
        user_goal_text="g",
    )
    out = build_planning_phase_output_from_step_statuses(
        [
            StepStatusEntry(order=1, tool_name="run_pipeline", mcp_status="skipped", label="p"),
        ],
        interpreted_goal=ig,
    )
    assert out["step_count"] == 1
    assert out["ordered_plan"][0]["mcp_status"] == "skipped"


def test_critic_and_report_phase_outputs() -> None:
    c = CriticAgentLLMOutput(
        findings_assessment="A" * 500,
        caveat_coverage="B",
        trustworthiness_notes="C",
        issues=["one", "two"],
        overall_confidence="low",
    )
    co = build_critic_phase_output(c, prose_max=80)
    assert co["issue_count"] == 2
    assert "low_overall_confidence" in co["weak_evidence_signals"]
    assert len(co["findings_assessment_excerpt"]) <= 82

    r = ReportAgentLLMOutput(
        user_report_markdown="# Hi\n\n" + "x" * 600,
        key_takeaways=["a"],
        narrative_thesis="Revenue growth is weakening, but the signal is still cautious rather than decisive.",
        narrative_whats_happening="Recent quarterly summaries flag repeated revenue-growth deterioration.",
        narrative_why_we_think_that="The summarized findings point to consecutive weak Q1 shifts in the loaded periods.",
        narrative_what_weakens_claim="Peer validation is thin, so the trend should be treated cautiously.",
    )
    ro = build_report_phase_output(r, {"panel_csv": "/tmp/panel.csv"})
    assert ro["artifact_refs"][0]["role"] == "panel_csv"
    assert ro["artifact_refs"][0]["basename"] == "panel.csv"
    assert ro["markdown_char_count"] > 600
    assert ro["narrative_answer"]["thesis"].startswith("Revenue growth is weakening")
