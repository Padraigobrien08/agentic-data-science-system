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
    run_root = tmp_path / "run-123"
    processed_dir = run_root / "processed"
    artifacts_dir = run_root / "artifacts"
    paths = {
        "panel": processed_dir / "panel.csv",
        "features": processed_dir / "features.csv",
        "anomalies": artifacts_dir / "anomalies.csv",
        "report": artifacts_dir / "report.md",
        "metric_coverage_summary": artifacts_dir / "metric_coverage_summary.csv",
        "metric_coverage_by_company": artifacts_dir / "metric_coverage_by_company.csv",
        "metric_coverage_by_period": artifacts_dir / "metric_coverage_by_period.csv",
        "metric_caveats_extraction": artifacts_dir / "metric_caveats_extraction.csv",
        "metric_caveats_panel": artifacts_dir / "metric_caveats_panel.csv",
        "data_quality": artifacts_dir / "data_quality_summary.csv",
        "exclusions": artifacts_dir / "exclusions_summary.csv",
        "peer_signals": artifacts_dir / "peer_signals.csv",
        "trend_breaks": artifacts_dir / "trend_break_signals.csv",
        "unified_findings": artifacts_dir / "unified_findings.csv",
        "findings_summary_by_company": artifacts_dir / "findings_summary_by_company.csv",
        "findings_summary_by_metric": artifacts_dir / "findings_summary_by_metric.csv",
        "findings_summary_by_period": artifacts_dir / "findings_summary_by_period.csv",
    }
    for p in paths.values():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("x", encoding="utf-8")
    return paths
