"""Interpreted-goal fields survive intent ``phase_output`` serialization (JSON-safe)."""

from __future__ import annotations

import json

from backend.agents.phase_outputs import build_intent_phase_output
from edgar_project.orchestration.planner import Planner
from edgar_project.orchestration.schemas import OrchestrationInput
from tests.orchestration.test_planner_alignment_regression import (
    GOAL_DETERIORATION_PERSISTENT_NOT_ONE_OFF,
    GOAL_PEER_UNDERPERFORMERS,
)


def test_intent_phase_output_persists_goal_preferences_and_plan_template() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT"],
            analysis_goal=GOAL_PEER_UNDERPERFORMERS,
            refresh=False,
        )
    )
    assert out.ok and out.interpreted_goal
    row = build_intent_phase_output(
        interpreted_goal=out.interpreted_goal,
        tickers=["AAPL", "MSFT"],
        analysis_goal=GOAL_PEER_UNDERPERFORMERS,
        source="deterministic_rules",
    )
    blob = json.dumps(row)
    restored = json.loads(blob)
    assert restored["goal_code"] == "peer_comparison"
    assert restored["plan_template"]["template_id"] == "peer_comparison"
    assert restored["goal_preferences"]["primary_analysis_mode"] == "peer_comparison"
    pt = restored["planning_transparency"]
    assert pt["present"] is True
    assert pt["plan_template_id"] == "peer_comparison"


def test_intent_phase_output_round_trip_deterioration_preferences() -> None:
    p = Planner()
    out = p.build_plan(
        OrchestrationInput(
            tickers=["AAPL", "MSFT", "NVDA"],
            analysis_goal=GOAL_DETERIORATION_PERSISTENT_NOT_ONE_OFF,
            refresh=False,
        )
    )
    assert out.ok and out.interpreted_goal
    row = build_intent_phase_output(
        interpreted_goal=out.interpreted_goal,
        tickers=["AAPL", "MSFT", "NVDA"],
        analysis_goal=GOAL_DETERIORATION_PERSISTENT_NOT_ONE_OFF,
        source="deterministic_rules",
    )
    restored = json.loads(json.dumps(row))
    assert restored["goal_preferences"]["preferred_signal_style"] == "persistent"
    assert restored["goal_preferences"]["directional_focus"] == "negative"
    assert restored["planning_transparency"]["directional_focus"] == "negative"
