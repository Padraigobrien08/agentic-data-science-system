"""Critic/report excerpt collection from orchestration artifact_paths."""

from __future__ import annotations

from pathlib import Path

from backend.agents.critic_artifact_keys import collect_critic_excerpts
from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
)


def test_collect_includes_anomalies_and_panel(tmp_path: Path) -> None:
    ap = tmp_path / "a.csv"
    ap.write_text("ticker,metric,z\nAAPL,rev,2.1\n", encoding="utf-8")
    pp = tmp_path / "p.csv"
    pp.write_text("ticker,fy\nAAPL,2023\n", encoding="utf-8")
    paths = {
        ARTIFACT_KEY_ANOMALIES: str(ap),
        ARTIFACT_KEY_PANEL: str(pp),
    }
    out = collect_critic_excerpts(paths)
    assert ARTIFACT_KEY_ANOMALIES in out
    assert "AAPL" in out[ARTIFACT_KEY_ANOMALIES]
    assert ARTIFACT_KEY_PANEL in out


def test_collect_skips_missing_paths() -> None:
    out = collect_critic_excerpts({ARTIFACT_KEY_UNIFIED_FINDINGS: "/no/such/file.csv"})
    assert out == {}


def test_every_analysis_artifact_role_is_reviewable_by_the_critic() -> None:
    """Artifacts the pipeline produces must be reachable by the critic and report.

    CRITIC_EXCERPT_PLAN is an allow-list, and the critic prompt tells the model to flag
    roles that have a path but no summary. So any artifact the pipeline writes but the
    plan omits is permanently in that state: the critic reports it as missing evidence
    on every run, and the answer cites a weakness that is an artifact of our own context
    building rather than of the data.

    That is what happened with the metric-coverage family — produced, registered, and
    never summarized, so "no metric coverage summary" surfaced as a top weakness in
    every answer. Asserting the whole set rather than the three roles that were missing
    means the next artifact added to the pipeline cannot quietly repeat it.

    The raw SEC response caches are deliberately excluded: they are unbounded upstream
    JSON, not analysis evidence.
    """
    import edgar_project.mcp.schemas as schemas
    from backend.agents.critic_artifact_keys import CRITIC_EXCERPT_PLAN

    raw_upstream_caches = {"cache_companyfacts_json", "cache_submissions_json"}
    all_roles = {
        value
        for name, value in vars(schemas).items()
        if name.startswith("ARTIFACT_KEY_") and isinstance(value, str)
    }
    planned = {role for role, _ in CRITIC_EXCERPT_PLAN}

    missing = all_roles - planned - raw_upstream_caches
    assert not missing, (
        f"artifact roles produced but never summarized for the critic: {sorted(missing)}"
    )

    # The plan is order-sensitive and de-duplicated by construction.
    planned_list = [role for role, _ in CRITIC_EXCERPT_PLAN]
    assert len(planned_list) == len(planned), "duplicate role in CRITIC_EXCERPT_PLAN"
    assert all(cap > 0 for _, cap in CRITIC_EXCERPT_PLAN), "every role needs a positive cap"
