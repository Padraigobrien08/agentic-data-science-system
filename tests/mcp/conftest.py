"""Shared fixtures for MCP tests."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture
def sample_panel_row() -> pd.DataFrame:
    """Minimal non-empty wide panel (one row)."""
    return pd.DataFrame(
        {
            "cik": [320193],
            "period": ["2021-Q1"],
            "revenue": [1.0e9],
            "net_income": [1.0e8],
        }
    )


@pytest.fixture
def tmp_artifact_paths(tmp_path: Path) -> dict[str, Path]:
    """Phase-1-like paths with files present (for ``artifact_info`` mtime)."""
    paths = {
        "panel": tmp_path / "panel.csv",
        "features": tmp_path / "features.csv",
        "anomalies": tmp_path / "anomalies.csv",
        "report": tmp_path / "report.md",
        "metric_coverage_summary": tmp_path / "metric_coverage_summary.csv",
        "metric_coverage_by_company": tmp_path / "metric_coverage_by_company.csv",
        "metric_coverage_by_period": tmp_path / "metric_coverage_by_period.csv",
        "metric_caveats_extraction": tmp_path / "metric_caveats_extraction.csv",
        "metric_caveats_panel": tmp_path / "metric_caveats_panel.csv",
        "data_quality": tmp_path / "data_quality_summary.csv",
        "exclusions": tmp_path / "exclusions_summary.csv",
        "peer_signals": tmp_path / "peer_signals.csv",
        "trend_breaks": tmp_path / "trend_break_signals.csv",
        "unified_findings": tmp_path / "unified_findings.csv",
        "findings_summary_by_company": tmp_path / "findings_summary_by_company.csv",
        "findings_summary_by_metric": tmp_path / "findings_summary_by_metric.csv",
        "findings_summary_by_period": tmp_path / "findings_summary_by_period.csv",
    }
    for p in paths.values():
        p.write_text("x", encoding="utf-8")
    return paths
