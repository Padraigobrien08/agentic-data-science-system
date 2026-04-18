"""Deterministic prompt-scope extraction for workspace ticker subsets."""

from __future__ import annotations

from edgar_project.orchestration.prompt_scope import extract_prompt_scope


def test_extract_prompt_scope_narrows_to_in_scope_subset() -> None:
    scope = extract_prompt_scope(
        "Analyze MSFT over the last 8 quarters",
        ["AAPL", "MSFT", "NVDA"],
    )

    assert scope.matched_workspace_tickers == ["MSFT"]
    assert scope.out_of_scope_tickers == []
    assert scope.effective_tickers == ["MSFT"]


def test_extract_prompt_scope_tracks_out_of_scope_tickers_without_expanding() -> None:
    scope = extract_prompt_scope(
        "Analyze TSLA margin pressure",
        ["AAPL", "MSFT", "NVDA"],
    )

    assert scope.matched_workspace_tickers == []
    assert scope.out_of_scope_tickers == ["TSLA"]
    assert scope.effective_tickers == ["AAPL", "MSFT", "NVDA"]
