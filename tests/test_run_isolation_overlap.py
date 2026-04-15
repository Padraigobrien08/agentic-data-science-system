"""Regression tests for overlapping run artifact isolation."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from edgar_project.run_workspace import build_run_workspace
from src.pipeline_runner import write_all_phase1_artifacts


def _minimal_panel() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cik": [1],
            "period": ["2021-Q1"],
            "revenue": [100.0],
            "net_income": [10.0],
            "total_assets": [1000.0],
            "total_liabilities": [400.0],
            "operating_cash_flow": [5.0],
            "current_assets": [100.0],
            "current_liabilities": [50.0],
            "revenue_growth_qoq": [0.0],
            "net_margin": [0.1],
            "current_ratio": [2.0],
            "debt_to_assets": [0.4],
        }
    )


def test_overlapping_runs_keep_distinct_artifact_paths(tmp_path: Path) -> None:
    run_a = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-a",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    ).ensure_directories()
    run_b = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-b",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    ).ensure_directories()

    panel = _minimal_panel()
    paths_a = write_all_phase1_artifacts(
        panel=panel,
        features=panel.copy(),
        anomalies=pd.DataFrame(),
        report_markdown="# Report A\n",
        workspace=run_a,
    )
    paths_b = write_all_phase1_artifacts(
        panel=panel,
        features=panel.copy(),
        anomalies=pd.DataFrame(),
        report_markdown="# Report B\n",
        workspace=run_b,
    )
    tracked_roles = ("panel", "features", "anomalies", "report", "unified_findings")

    assert all(paths_a[role] != paths_b[role] for role in tracked_roles)
    assert all(paths_a[role].is_file() for role in tracked_roles)
    assert all(paths_b[role].is_file() for role in tracked_roles)
    assert "run-a" in paths_a["report"].as_posix()
    assert "run-b" in paths_b["report"].as_posix()
