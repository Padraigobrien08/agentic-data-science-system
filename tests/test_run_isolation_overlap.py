"""Wave 0 regression seed for overlapping run artifact isolation."""

from __future__ import annotations

from pathlib import Path

import pytest

from edgar_project.run_workspace import build_run_workspace
from src.pipeline_runner import phase1_paths


def test_overlapping_runs_keep_distinct_artifact_paths(tmp_path: Path) -> None:
    run_a = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-a",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    )
    run_b = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-b",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    )

    paths_a = phase1_paths(run_a)
    paths_b = phase1_paths(run_b)
    tracked_roles = ("panel", "features", "anomalies", "report", "unified_findings")

    assert all(paths_a[role] != paths_b[role] for role in tracked_roles)
    pytest.skip(
        "Wave 0 seed: later plans must prove overlapping executions keep these artifact paths distinct end-to-end."
    )
