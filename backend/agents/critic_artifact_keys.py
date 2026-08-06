"""
Artifact roles for critic/report LLM context (bounded UTF-8 excerpts).

Paths come from :attr:`~edgar_project.orchestration.schemas.OrchestrationOutput.artifact_paths`.
Previously the critic only read unified_findings + metric caveats; typical runs expose rich
``anomalies_csv`` / ``report_md`` / ``features_csv`` / ``panel_csv`` but those were ignored,
so models saw empty excerpts and produced hollow narratives.
"""

from __future__ import annotations

from backend.agents.artifact_excerpts import read_text_excerpt
from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_DATA_QUALITY,
    ARTIFACT_KEY_DETERIORATION_FOCUS,
    ARTIFACT_KEY_EXCLUSIONS,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD,
    ARTIFACT_KEY_MANUAL_VALIDATION,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD,
    ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_REPORT,
    ARTIFACT_KEY_TREND_BREAKS,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
)

# Order matters: highest-signal tables first. Per-role UTF-8 char caps (truncated excerpts).
CRITIC_EXCERPT_PLAN: tuple[tuple[str, int], ...] = (
    (ARTIFACT_KEY_ANOMALIES, 14_000),
    (ARTIFACT_KEY_UNIFIED_FINDINGS, 12_000),
    (ARTIFACT_KEY_DETERIORATION_FOCUS, 9_000),
    (ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY, 7_000),
    (ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC, 7_000),
    (ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD, 7_000),
    (ARTIFACT_KEY_REPORT, 12_000),
    (ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION, 8_000),
    (ARTIFACT_KEY_METRIC_CAVEATS_PANEL, 8_000),
    (ARTIFACT_KEY_MANUAL_VALIDATION, 6_000),
    (ARTIFACT_KEY_FEATURES, 7_000),
    (ARTIFACT_KEY_PANEL, 5_000),
    (ARTIFACT_KEY_DATA_QUALITY, 5_000),
    # Coverage sits with data quality: both answer "can this evidence be trusted?", which
    # the critic is explicitly asked to judge. These were produced and registered by the
    # pipeline but missing from this plan, so they were permanently in the "has a path,
    # no summary" state the critic is told to flag — meaning every run reported a missing
    # metric coverage summary as a top weakness of its own analysis. The summary table is
    # ~250 bytes; all three together are ~5 KB against a ~21k-token prompt.
    (ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY, 5_000),
    (ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY, 5_000),
    (ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD, 6_000),
    (ARTIFACT_KEY_EXCLUSIONS, 5_000),
    (ARTIFACT_KEY_PEER_SIGNALS, 5_000),
    (ARTIFACT_KEY_TREND_BREAKS, 5_000),
)


def collect_critic_excerpts(
    artifact_paths: dict[str, str],
    *,
    max_chars_per_file: int | None = None,
) -> dict[str, str]:
    """
    Role → excerpt text. Uses :data:`CRITIC_EXCERPT_PLAN` for ordering and per-role limits.

    ``max_chars_per_file`` is legacy: when set, every role uses that cap instead of the plan.
    """
    out: dict[str, str] = {}
    if max_chars_per_file is not None:
        for role, p in CRITIC_EXCERPT_PLAN:
            path = artifact_paths.get(role)
            if not path:
                continue
            ex = read_text_excerpt(path, max_chars=max_chars_per_file)
            if ex:
                out[role] = ex
    else:
        for role, cap in CRITIC_EXCERPT_PLAN:
            p = artifact_paths.get(role)
            if not p:
                continue
            ex = read_text_excerpt(p, max_chars=cap)
            if ex:
                out[role] = ex

    for role, p in sorted(artifact_paths.items()):
        if "trustworthiness" in role.lower() and role not in out:
            cap = max_chars_per_file if max_chars_per_file is not None else 8_000
            ex = read_text_excerpt(p, max_chars=cap)
            if ex:
                out[role] = ex
    return out
