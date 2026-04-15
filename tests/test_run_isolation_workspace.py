"""Contract tests for run-scoped workspaces."""

from __future__ import annotations

from pathlib import Path

import config

from edgar_project.run_workspace import build_run_workspace


def test_build_run_workspace(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    manual_validation_csv = Path("/repo/validation/manual_validation.csv")

    workspace = build_run_workspace(
        workspace_root=workspace_root,
        run_scoped_id="run-123",
        manual_validation_csv=manual_validation_csv,
    )

    assert workspace.run_scoped_id == "run-123"
    assert workspace.root == workspace_root / "run-123"
    assert workspace.processed_dir == workspace.root / "processed"
    assert workspace.artifacts_dir == workspace.root / "artifacts"
    assert workspace.manual_validation_csv == manual_validation_csv
    assert workspace.use_legacy_shared_paths is False


def test_build_run_workspace_legacy_shared_paths(tmp_path: Path) -> None:
    workspace_root = tmp_path / "workspaces"
    manual_validation_csv = Path("/repo/validation/manual_validation.csv")

    workspace = build_run_workspace(
        workspace_root=workspace_root,
        run_scoped_id="run-123",
        manual_validation_csv=manual_validation_csv,
        use_legacy_shared_paths=True,
    )

    assert workspace.root == workspace_root / "run-123"
    assert workspace.processed_dir == config.DATA_PROCESSED
    assert workspace.artifacts_dir == config.DATA_ARTIFACTS
    assert workspace.manual_validation_csv == manual_validation_csv
    assert workspace.use_legacy_shared_paths is True
