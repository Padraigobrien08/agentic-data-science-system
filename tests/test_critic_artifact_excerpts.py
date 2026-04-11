"""Critic/report excerpt collection from orchestration artifact_paths."""

from __future__ import annotations

from pathlib import Path

from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
)

from backend.agents.critic_artifact_keys import collect_critic_excerpts


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
