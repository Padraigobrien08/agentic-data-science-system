"""
Rule-based natural-language intent for orchestration (no LLM).

Evaluates ``analysis_goal`` text in fixed priority order; each branch is a small,
inspectable predicate. See :func:`interpret_goal_intent` and rule id strings returned
in :attr:`IntentInterpretation.rules_matched`.

**Relationship to preferences:** this module only picks a coarse
:class:`~edgar_project.orchestration.schemas.OrchestrationIntent`. Fine-grained routing
(``primary_analysis_mode``, signal style, peer *preference* tier) lives in
:mod:`edgar_project.orchestration.goal_preferences` on the same user text. Peer-vs-peer
reporting is gated here first; keyword overlap between the two layers is intentional
but not identical (e.g. bare “compare” does not imply peer intent).

Pure string/regex classification only—no I/O, MCP, or filesystem access.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final

from edgar_project.orchestration.schemas import OrchestrationIntent


@dataclass(frozen=True, slots=True)
class IntentInterpretation:
    """Result of deterministic intent parsing."""

    intent: OrchestrationIntent
    rules_matched: tuple[str, ...]
    normalized_text: str


# --- full_pipeline_run (checked first: explicit “run the pipeline” style) ---

_FULL_PIPELINE_REGEX: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"\brun\s+(the\s+)?pipeline\b"), "regex:run_the_pipeline"),
    (re.compile(r"\bfull\s+pipeline\b"), "regex:full_pipeline"),
    (re.compile(r"\bexecute\s+(the\s+)?pipeline\b"), "regex:execute_pipeline"),
    (re.compile(r"\bpipeline\s+run\b"), "regex:pipeline_run"),
    (re.compile(r"\brun\s+.*\bpipeline\b"), "regex:run_*_pipeline"),
)


def _try_full_pipeline(compact: str) -> tuple[str, ...] | None:
    for pat, rule_id in _FULL_PIPELINE_REGEX:
        if pat.search(compact):
            return (rule_id,)
    return None


# --- peer_report (compare / peer language + report or generate) ---

_PEER_COMPARISON_REGEX: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (re.compile(r"\bvs\.?\b"), "regex:vs"),
    (re.compile(r"\bversus\b"), "regex:versus"),
    (re.compile(r"\brelative\s+to\b"), "regex:relative_to"),
    (re.compile(r"\bweaker\b"), "regex:weaker"),
    (re.compile(r"\bstronger\b"), "regex:stronger"),
    (re.compile(r"\bunderperform\w*\b"), "regex:underperform"),
    (re.compile(r"\boutperform\w*\b"), "regex:outperform"),
    (re.compile(r"\bwhich\s+company\b"), "regex:which_company"),
)


def _extract_ticker_like_tokens(goal_text: str) -> list[str]:
    tokens: list[str] = []
    seen: set[str] = set()
    for raw_token in re.split(r"[^A-Za-z0-9]+", goal_text):
        token = raw_token.strip()
        if (
            not token
            or token in seen
            or not token.isalpha()
            or token != token.upper()
            or re.match(r"^[A-Z]{1,5}$", token) is None
        ):
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _dedupe_rules(rules: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(rules))


def _try_peer_report(goal_text: str, compact: str) -> tuple[str, ...] | None:
    rules: list[str] = []
    if "peer report" in compact:
        return ("phrase:peer_report",)
    has_compare = bool(re.search(r"\bcompare\b", compact))
    has_peer = bool(re.search(r"\bpeers?\b", compact))
    has_company = bool(re.search(r"\bcompan(?:y|ies)\b", compact))
    has_report = "report" in compact
    has_generate = "generate" in compact
    has_ticker_pair = len(_extract_ticker_like_tokens(goal_text)) >= 2
    comparison_rules = [
        rule_id for pattern, rule_id in _PEER_COMPARISON_REGEX if pattern.search(compact)
    ]
    if has_peer and has_report:
        rules.append("combo:peer+report")
    if has_compare and (has_report or has_generate):
        rules.append("combo:compare+(report|generate)")
    if has_compare and "compan" in compact and (has_report or has_generate):
        rules.append("combo:compare_companies+output")
    # Compare + peers without explicit "report" / "generate" (e.g. highlight underperformers).
    if has_compare and has_peer and (
        has_report
        or has_generate
        or "underperform" in compact
        or re.search(r"\bhighlight\b", compact) is not None
    ):
        rules.append("combo:compare+peers+emphasis_or_output")
    if comparison_rules and (has_ticker_pair or has_company or has_peer or has_compare):
        rules.extend(comparison_rules)
        if has_ticker_pair:
            rules.append("context:ticker_pair")
        if has_company:
            rules.append("context:company_word")
    if rules:
        return _dedupe_rules(rules)
    return None


# --- anomaly_analysis (unusual / anomaly / outlier / trend / detection language) ---

_ANOMALY_PHRASES: Final[tuple[tuple[str, str], ...]] = (
    ("unusual financial", "phrase:unusual_financial"),
    ("unusual changes", "phrase:unusual_changes"),
    ("unusual change", "phrase:unusual_change"),
    ("financial anomalies", "phrase:financial_anomalies"),
    ("find unusual", "phrase:find_unusual"),
    ("detect anomalies", "phrase:detect_anomalies"),
    ("anomaly detection", "phrase:anomaly_detection"),
)

_ANOMALY_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "anomaly",
        "anomalies",
        "unusual",
        "outlier",
        "outliers",
        "zscore",
        "z-score",
        "z score",
        "trend",
        "trends",
        "detect",
        "detection",
    }
)

_ANALYST_CORE_PHRASES: Final[tuple[tuple[str, str], ...]] = (
    ("margin pressure", "phrase:margin_pressure"),
    ("temporary or structural", "phrase:temporary_or_structural"),
    ("cash flow quality", "phrase:cash_flow_quality"),
    ("slipping", "phrase:slipping"),
)

_ANALYST_SUPPORTING_PHRASES: Final[tuple[tuple[str, str], ...]] = (
    ("persistent", "phrase:persistent"),
    ("sustained", "phrase:sustained"),
    ("last eight quarters", "phrase:last_eight_quarters"),
    ("last 8 quarters", "phrase:last_8_quarters"),
)

_ANALYST_SUPPORTING_REGEX: Final[tuple[tuple[re.Pattern[str], str], ...]] = (
    (
        re.compile(r"\b(?:margins?|cash\s+flow|revenue\s+growth|liquidity|leverage|debt)\b"),
        "regex:metric_cue",
    ),
    (
        re.compile(r"\b(?:over\s+recent\s+quarters|recent\s+quarters|last\s+(?:8|eight)\s+quarters)\b"),
        "regex:time_cue",
    ),
)


def _tokenize(compact: str) -> set[str]:
    raw = re.split(r"[^\w\-]+", compact.lower())
    words = {w for w in raw if w}
    parts = compact.split()
    for i in range(len(parts) - 1):
        words.add(f"{parts[i]} {parts[i + 1]}")
    return words


def _try_anomaly_analysis(compact: str) -> tuple[str, ...] | None:
    for phrase, rule_id in _ANOMALY_PHRASES:
        if phrase in compact:
            return (rule_id,)
    tokens = _tokenize(compact)
    hit = sorted(tokens & _ANOMALY_TOKENS)
    if hit:
        return ("tokens:" + "+".join(hit[:6]),)
    analyst_rules = [
        rule_id for phrase, rule_id in _ANALYST_CORE_PHRASES if phrase in compact
    ]
    if analyst_rules:
        analyst_rules.extend(
            rule_id for phrase, rule_id in _ANALYST_SUPPORTING_PHRASES if phrase in compact
        )
        analyst_rules.extend(
            rule_id for pattern, rule_id in _ANALYST_SUPPORTING_REGEX if pattern.search(compact)
        )
        return _dedupe_rules(analyst_rules)
    supporting_hits = [
        rule_id for phrase, rule_id in _ANALYST_SUPPORTING_PHRASES if phrase in compact
    ]
    regex_hits = [
        rule_id for pattern, rule_id in _ANALYST_SUPPORTING_REGEX if pattern.search(compact)
    ]
    if supporting_hits and regex_hits:
        return _dedupe_rules(supporting_hits + regex_hits)
    return None


def interpret_goal_intent(goal_text: str) -> IntentInterpretation | None:
    """
    Map user ``analysis_goal`` to a supported :class:`OrchestrationIntent`.

    Returns ``None`` when no rule matches (caller should surface a validation error).
    Priority: ``full_pipeline_run`` → ``peer_report`` → ``anomaly_analysis``.
    """
    normalized = goal_text.strip()
    compact = re.sub(r"\s+", " ", normalized.lower())

    matched = _try_full_pipeline(compact)
    if matched:
        return IntentInterpretation(OrchestrationIntent.full_pipeline_run, matched, normalized)

    matched = _try_peer_report(normalized, compact)
    if matched:
        return IntentInterpretation(OrchestrationIntent.peer_report, matched, normalized)

    matched = _try_anomaly_analysis(compact)
    if matched:
        return IntentInterpretation(OrchestrationIntent.anomaly_analysis, matched, normalized)

    return None


def supported_intents_summary() -> str:
    """Short list for validation error messages."""
    return ", ".join(sorted(e.value for e in OrchestrationIntent))
