"""Deterministic intent interpreter (no MCP)."""

from __future__ import annotations

from edgar_project.orchestration.intent import interpret_goal_intent
from edgar_project.orchestration.schemas import OrchestrationIntent


def test_examples_from_spec() -> None:
    a = interpret_goal_intent("find unusual financial changes")
    assert a is not None
    assert a.intent == OrchestrationIntent.anomaly_analysis
    assert any("unusual" in r or "phrase" in r for r in a.rules_matched)

    p = interpret_goal_intent("compare these companies and generate a report")
    assert p is not None
    assert p.intent == OrchestrationIntent.peer_report

    f = interpret_goal_intent("run the pipeline for these tickers")
    assert f is not None
    assert f.intent == OrchestrationIntent.full_pipeline_run


def test_unsupported_returns_none() -> None:
    assert interpret_goal_intent("hello world") is None
    assert interpret_goal_intent("   ") is None  # stripped empty might still be min_length 1 on input - here direct call


def test_priority_full_pipeline_over_anomaly_keywords() -> None:
    """Explicit pipeline run wins even if other words appear."""
    x = interpret_goal_intent("run the pipeline and check for anomalies")
    assert x is not None
    assert x.intent == OrchestrationIntent.full_pipeline_run
