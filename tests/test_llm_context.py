"""Compact LLM context builders — shape and bounds."""

from __future__ import annotations

from edgar_project.orchestration.plan_templates import get_plan_template_snapshot
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationOutput,
    OrchestrationRunStatus,
    PlanTemplateId,
)

from backend.agents.llm_context import (
    CONTRACT_CRITIC_LLM,
    CONTRACT_INTENT_LLM,
    CONTRACT_PLANNING_LLM,
    CONTRACT_REPORT_LLM,
    audit_compact_context,
    build_critic_llm_context,
    build_intent_llm_context,
    build_planning_llm_context,
    build_report_llm_context,
)


def _minimal_ig() -> InterpretedGoal:
    snap = get_plan_template_snapshot(PlanTemplateId.trend_deterioration)
    return InterpretedGoal(
        code=InterpretedGoalCode.trend_deterioration,
        intent=None,
        intent_rules_matched=["x"],
        description="d",
        user_goal_text="goal text",
        goal_preferences=None,
        plan_template=snap,
    )


def test_build_intent_llm_context() -> None:
    d = build_intent_llm_context(user_request="hello", tickers=["A"], refresh=False)
    assert d["contract_version"] == CONTRACT_INTENT_LLM
    assert d["tickers"] == ["A"]


def test_build_planning_llm_context_has_slim_goal() -> None:
    ig = _minimal_ig()
    d = build_planning_llm_context(
        interpreted_goal=ig,
        user_request="u",
        tickers=["A"],
        refresh=True,
    )
    assert d["contract_version"] == CONTRACT_PLANNING_LLM
    assert "ordered_phases" not in (d["interpreted_goal"].get("plan_template") or {})


def test_critic_and_report_contract_versions() -> None:
    ig = _minimal_ig()
    orch = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=ig,
    )
    inp = OrchestrationInput(tickers=["A"], analysis_goal="g", refresh=False)
    summaries = {
        "contract_version": "artifact_summaries_v1",
        "by_role": {"anomalies_csv": {"kind": "anomalies_csv", "top_rows": []}},
        "artifact_index": [],
    }
    c = build_critic_llm_context(
        orch=orch,
        orch_input=inp,
        plan_alignment_findings=[],
        artifact_summaries=summaries,
        paths_roles=["a"],
        summary_roles_loaded=["anomalies_csv"],
    )
    assert c["contract_version"] == CONTRACT_CRITIC_LLM
    assert "tool_scope" in c
    assert c["artifact_summaries"]["by_role"]["anomalies_csv"]["kind"] == "anomalies_csv"
    aud = audit_compact_context(c)
    assert aud["approx_json_chars"] > 0
    assert "anomalies_csv" in aud["roles_with_summaries"]

    r = build_report_llm_context(
        orch=orch,
        orch_input=inp,
        critic={"overall_confidence": "high"},
        artifact_summaries=summaries,
        paths_roles=["a"],
        summary_roles_loaded=["anomalies_csv"],
    )
    assert r["contract_version"] == CONTRACT_REPORT_LLM
    assert r["critic"] == {"overall_confidence": "high"}
