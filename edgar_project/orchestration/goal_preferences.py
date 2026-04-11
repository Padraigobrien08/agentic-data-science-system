"""
Deterministic extraction of :class:`GoalPreferences` from ``analysis_goal`` text (no LLM).

Used by :class:`~edgar_project.orchestration.planner.Planner` to choose between the
granular anomaly path and a single-step ``run_pipeline`` call that produces trend breaks,
unified findings, peer signals, and coverage artifacts.
"""

from __future__ import annotations

import re
from typing import Final

from edgar_project.orchestration.schemas import (
    DirectionalFocus,
    GoalPreferences,
    MetricPriority,
    PeerRequirement,
    PreferredSignalStyle,
    PrimaryAnalysisMode,
    TimeFocus,
)

_MAX_METRICS: Final[int] = 5

# --- keyword groups (lowercased compact text) ---

_DETERIORATION: Final[tuple[str, ...]] = (
    "deterioration",
    "deteriorate",
    "deteriorating",
    "distress",
    "financial stress",
    "weakening",
    "weaken",
    "weakness",
    "declining",
    "decline",
    "slowing",
    "slowdown",
    "slowed",
    "compressing",
    "compression",
    "margin pressure",
    "underperformance",
)

_TREND: Final[tuple[str, ...]] = (
    "trend",
    "trends",
    "trajectory",
    "over time",
    "multi-quarter",
    "multi quarter",
    "several quarters",
    "rolling",
)

_PEER: Final[tuple[str, ...]] = (
    "peer",
    "peers",
    "vs peers",
    "versus peers",
    "industry",
    "relative to",
    "benchmark",
    "compare",
    "comparison",
)

_ANOMALY: Final[tuple[str, ...]] = (
    "anomaly",
    "anomalies",
    "outlier",
    "outliers",
    "unusual",
    "z-score",
    "zscore",
    "spike",
)

_PERSISTENT: Final[tuple[str, ...]] = (
    "persistent",
    "persist",
    "sustained",
    "ongoing",
    "prolonged",
    "rather than one-off",
    "not one-off",
    "not just one-off",
    "instead of one-off",
    "avoid one-off",
)

_ONE_OFF: Final[tuple[str, ...]] = (
    "one-off",
    "one off",
    "single quarter",
    "single-quarter",
    "spike only",
)

_NEGATIVE: Final[tuple[str, ...]] = (
    "declining",
    "decline",
    "slowing",
    "weakening",
    "negative",
    "deterioration",
    "compress",
    "weak",
    "worse",
)

_POSITIVE: Final[tuple[str, ...]] = (
    "growth",
    "improving",
    "improvement",
    "positive",
    "strong",
    "expanding",
    "better",
)

_RECENT_TIME: Final[tuple[str, ...]] = (
    "recent quarter",
    "recent quarters",
    "last few quarter",
    "past few quarter",
    "trailing",
    "yoy",
    "year over year",
)

_FULL_HISTORY: Final[tuple[str, ...]] = (
    "full history",
    "all available",
    "entire series",
    "long history",
    "max history",
)

_METRIC_PATTERNS: Final[tuple[tuple[re.Pattern[str], MetricPriority, str], ...]] = (
    (re.compile(r"\bmargin\b"), MetricPriority.margins, "metric:margins"),
    (re.compile(r"\brevenue\s+growth\b"), MetricPriority.revenue_growth, "metric:revenue_growth"),
    (re.compile(r"\brevenue\b"), MetricPriority.revenue_growth, "metric:revenue"),
    (re.compile(r"\bcash\s+flow\b"), MetricPriority.cash_flow, "metric:cash_flow"),
    (re.compile(r"\bliquidity\b"), MetricPriority.liquidity, "metric:liquidity"),
    (re.compile(r"\bleverage\b|\bdebt\b"), MetricPriority.leverage, "metric:leverage"),
)


def _count_phrase_hits(compact: str, phrases: tuple[str, ...]) -> int:
    return sum(1 for p in phrases if p in compact)


def _resolve_primary_mode(
    compact: str,
    *,
    det: int,
    tr: int,
    peer: int,
    anom: int,
    rules: list[str],
) -> PrimaryAnalysisMode:
    """Pick a single primary mode; emit mixed when multiple families compete."""
    scores: list[tuple[str, int, PrimaryAnalysisMode]] = [
        ("deterioration", det, PrimaryAnalysisMode.deterioration),
        ("trend", tr, PrimaryAnalysisMode.trend),
        ("peer", peer, PrimaryAnalysisMode.peer_comparison),
        ("anomaly", anom, PrimaryAnalysisMode.anomaly),
    ]
    nonzero = [(name, n, m) for name, n, m in scores if n > 0]
    if not nonzero:
        rules.append("primary:default_mixed")
        return PrimaryAnalysisMode.mixed

    max_n = max(x[1] for x in nonzero)
    top = [x for x in nonzero if x[1] == max_n]
    if len(top) > 1:
        modes_tied = {x[2] for x in top}
        if PrimaryAnalysisMode.deterioration in modes_tied and PrimaryAnalysisMode.trend in modes_tied:
            if det >= tr:
                rules.append("primary:tie_break_deterioration_over_trend")
                return PrimaryAnalysisMode.deterioration
        rules.append("primary:mixed_multi_signal")
        return PrimaryAnalysisMode.mixed
    rules.append(f"primary:dominant_{top[0][0]}")
    return top[0][2]


def _priority_metrics_ordered(compact: str, rules: list[str]) -> list[MetricPriority]:
    """Order metrics by first match position in the goal (user listing order)."""
    hits: list[tuple[int, MetricPriority, str]] = []
    for pat, metric, rule_id in _METRIC_PATTERNS:
        m = pat.search(compact)
        if m:
            hits.append((m.start(), metric, rule_id))
    hits.sort(key=lambda x: x[0])
    seen: set[MetricPriority] = set()
    out: list[MetricPriority] = []
    for _pos, metric, rule_id in hits:
        if metric in seen:
            continue
        seen.add(metric)
        out.append(metric)
        rules.append(rule_id)
        if len(out) >= _MAX_METRICS:
            break
    return out


def parse_goal_preferences(goal_text: str) -> GoalPreferences:
    """
    Rule-based :class:`GoalPreferences` from natural-language ``analysis_goal``.

    Intended for persistence on :class:`~edgar_project.orchestration.schemas.InterpretedGoal` and for
    planner routing (granular vs ``run_pipeline``).
    """
    normalized = goal_text.strip()
    compact = re.sub(r"\s+", " ", normalized.lower())
    rules: list[str] = []

    det = _count_phrase_hits(compact, _DETERIORATION)
    tr = _count_phrase_hits(compact, _TREND)
    peer = _count_phrase_hits(compact, _PEER)
    anom = _count_phrase_hits(compact, _ANOMALY)

    primary = _resolve_primary_mode(compact, det=det, tr=tr, peer=peer, anom=anom, rules=rules)

    persistent_hits = _count_phrase_hits(compact, _PERSISTENT)
    one_off_hits = _count_phrase_hits(compact, _ONE_OFF)
    if persistent_hits and not one_off_hits:
        pstyle = PreferredSignalStyle.persistent
        rules.append("signal:persistent_phrases")
    elif one_off_hits and not persistent_hits:
        pstyle = PreferredSignalStyle.one_off
        rules.append("signal:one_off_phrases")
    elif persistent_hits and one_off_hits:
        pstyle = PreferredSignalStyle.mixed
        rules.append("signal:mixed_persistent_and_one_off")
    else:
        pstyle = PreferredSignalStyle.mixed
        rules.append("signal:default_mixed")

    neg = _count_phrase_hits(compact, _NEGATIVE)
    pos = _count_phrase_hits(compact, _POSITIVE)
    if neg > pos:
        directional = DirectionalFocus.negative
        rules.append("direction:negative_dominant")
    elif pos > neg:
        directional = DirectionalFocus.positive
        rules.append("direction:positive_dominant")
    else:
        directional = DirectionalFocus.both
        rules.append("direction:balanced")

    metrics = _priority_metrics_ordered(compact, rules)

    if _count_phrase_hits(compact, _RECENT_TIME) and not _count_phrase_hits(compact, _FULL_HISTORY):
        time_f = TimeFocus.recent_quarters
        rules.append("time:recent")
    elif _count_phrase_hits(compact, _FULL_HISTORY) and not _count_phrase_hits(compact, _RECENT_TIME):
        time_f = TimeFocus.full_history
        rules.append("time:full_history")
    else:
        time_f = TimeFocus.mixed
        rules.append("time:mixed_or_unspecified")

    if re.search(r"\bpeers?\s+required\b|\brequire\s+peer\b|\bmust\s+include\s+peer", compact):
        peer_req = PeerRequirement.required
        rules.append("peer:required_phrase")
    elif peer >= 1:
        peer_req = PeerRequirement.optional
        rules.append("peer:optional_keywords")
    else:
        peer_req = PeerRequirement.none
        rules.append("peer:none")

    return GoalPreferences(
        primary_analysis_mode=primary,
        preferred_signal_style=pstyle,
        directional_focus=directional,
        priority_metrics=metrics,
        time_focus=time_f,
        peer_requirement=peer_req,
        preference_rules_matched=sorted(set(rules)),
        schema_version="1",
    )


def prefer_run_pipeline_over_granular(prefs: GoalPreferences) -> bool:
    """
    Whether to use ``run_pipeline`` (trend breaks, unified findings, peer/coverage) vs granular steps.

    Granular path remains the default for classic anomaly / z-score screens without
    sustained-trend or deterioration language.
    """
    m = prefs.primary_analysis_mode
    if m in (
        PrimaryAnalysisMode.deterioration,
        PrimaryAnalysisMode.trend,
        PrimaryAnalysisMode.peer_comparison,
    ):
        return True
    if prefs.peer_requirement == PeerRequirement.required:
        return True
    if m == PrimaryAnalysisMode.mixed:
        return True
    if m == PrimaryAnalysisMode.anomaly:
        return (
            prefs.preferred_signal_style == PreferredSignalStyle.persistent
            and prefs.directional_focus == DirectionalFocus.negative
        )
    return False
