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

    peer_highlight = interpret_goal_intent(
        "Compare these companies against peers and highlight underperformers."
    )
    assert peer_highlight is not None
    assert peer_highlight.intent == OrchestrationIntent.peer_report
    assert any("compare+peers" in r for r in peer_highlight.rules_matched)

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


def test_analyst_language_routes_to_anomaly_intent() -> None:
    interpretation = interpret_goal_intent(
        "Analyze MSFT over the last 8 quarters and tell me whether margin pressure is temporary or structural"
    )
    assert interpretation is not None
    assert interpretation.intent == OrchestrationIntent.anomaly_analysis
    assert any("margin_pressure" in rule or "temporary_or_structural" in rule for rule in interpretation.rules_matched)


def test_peer_relative_language_routes_to_peer_intent() -> None:
    prompts = (
        "AAPL vs MSFT on operating margins",
        "Compare AAPL versus MSFT on operating margins",
        "Which company is weaker, AAPL or MSFT, on free cash flow quality?",
    )

    for prompt in prompts:
        interpretation = interpret_goal_intent(prompt)
        assert interpretation is not None
        assert interpretation.intent == OrchestrationIntent.peer_report
