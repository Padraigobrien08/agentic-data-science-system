"""Deterministic planning transparency bundle (no LLM)."""

from __future__ import annotations

from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.planning_transparency import build_planning_transparency
from edgar_project.orchestration.schemas import OrchestrationInput


def test_build_planning_transparency_absent_goal() -> None:
    t = build_planning_transparency(None)
    assert t["present"] is False
    assert t["contract_version"] == "1"


def test_planner_goal_produces_rationale_and_emphasis() -> None:
    out = Planner().build_plan(
        OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="downward trends in margins and cash flow over recent quarters",
            refresh=False,
        )
    )
    assert out.ok and out.interpreted_goal
    tx = build_planning_transparency(out.interpreted_goal)
    assert tx["present"] is True
    assert tx.get("plan_template_id") == "trend_deterioration"
    assert tx.get("goal_code") == "trend_deterioration"
    assert tx.get("orchestration_intent") == "anomaly_analysis"
    assert "planning_rationale_summary" in tx and tx["planning_rationale_summary"]
    assert isinstance(tx.get("emphasized"), list)
    assert isinstance(tx.get("deemphasized"), list)
    sp = tx.get("selected_signal_preferences")
    assert isinstance(sp, dict)
    assert "primary_analysis_mode" in sp
