"""Deterministic extraction of prompt-named ticker scope from ``analysis_goal`` text."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Sequence

_TOKEN_SPLIT_RE = re.compile(r"[^A-Za-z0-9]+")
_TICKER_TOKEN_RE = re.compile(r"^[A-Z]{1,5}$")


@dataclass(frozen=True, slots=True)
class PromptScope:
    """Prompt-named ticker scope relative to the current workspace tickers."""

    matched_workspace_tickers: list[str]
    out_of_scope_tickers: list[str]
    effective_tickers: list[str]


def _normalize_workspace_tickers(workspace_tickers: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for ticker in workspace_tickers:
        normalized_ticker = str(ticker).strip().upper()
        if not normalized_ticker or normalized_ticker in seen:
            continue
        seen.add(normalized_ticker)
        normalized.append(normalized_ticker)
    return normalized


def _extract_uppercase_goal_tokens(analysis_goal: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw_token in _TOKEN_SPLIT_RE.split(analysis_goal):
        token = raw_token.strip()
        if not token or token in seen:
            continue
        if not token.isalpha() or token != token.upper():
            continue
        if _TICKER_TOKEN_RE.match(token) is None:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def extract_prompt_scope(analysis_goal: str, workspace_tickers: Sequence[str]) -> PromptScope:
    """
    Return the prompt-named ticker subset relative to the current workspace scope.

    Extraction is deterministic and symbol-based only for Phase 13. Company-name lookup
    and fuzzy matching are intentionally out of scope.
    """

    normalized_workspace_tickers = _normalize_workspace_tickers(workspace_tickers)
    workspace_ticker_set = set(normalized_workspace_tickers)

    matched_workspace_tickers: list[str] = []
    out_of_scope_tickers: list[str] = []
    for token in _extract_uppercase_goal_tokens(analysis_goal):
        if token in workspace_ticker_set:
            matched_workspace_tickers.append(token)
            continue
        out_of_scope_tickers.append(token)

    effective_tickers = (
        list(matched_workspace_tickers)
        if matched_workspace_tickers
        else list(normalized_workspace_tickers)
    )
    return PromptScope(
        matched_workspace_tickers=matched_workspace_tickers,
        out_of_scope_tickers=out_of_scope_tickers,
        effective_tickers=effective_tickers,
    )
