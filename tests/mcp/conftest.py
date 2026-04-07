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
        "data_quality": tmp_path / "data_quality_summary.csv",
        "exclusions": tmp_path / "exclusions_summary.csv",
        "peer_signals": tmp_path / "peer_signals.csv",
    }
    for p in paths.values():
        p.write_text("x", encoding="utf-8")
    return paths
