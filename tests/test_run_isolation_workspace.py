"""Contract tests for run-scoped workspaces."""

from __future__ import annotations

from pathlib import Path

import config
import pandas as pd
import pytest

from edgar_project.orchestration.execution_contract import ExecutionRequest
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationInput,
    OrchestrationIntent,
    OrchestrationPlan,
    PlannedStep,
    RunWorkspacePayload,
)
from edgar_project.run_workspace import build_run_workspace
from src.pipeline_runner import phase1_paths

# Future regression expansion is tracked in:
# - tests/test_run_isolation_overlap.py::test_overlapping_runs_keep_distinct_artifact_paths
# - tests/test_run_isolation_execution_service.py::test_execute_analysis_run_uses_explicit_workspace_paths


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


def test_workspace_paths_are_persisted_and_run_scoped(tmp_path: Path) -> None:
    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-123",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    )

    paths = phase1_paths(workspace)

    assert all(path.is_absolute() for path in paths.values())
    assert all(path.parent in {workspace.processed_dir.resolve(), workspace.artifacts_dir.resolve()} for path in paths.values())
    assert paths["panel"] == workspace.processed_dir / "panel.csv"
    assert paths["features"] == workspace.processed_dir / "features.csv"
    assert paths["anomalies"] == workspace.artifacts_dir / "anomalies.csv"
    assert paths["report"] == workspace.artifacts_dir / "report.md"


def test_manual_validation_csv_remains_explicit_input(tmp_path: Path) -> None:
    manual_validation_csv = Path("/repo/validation/manual_validation.csv")
    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-123",
        manual_validation_csv=manual_validation_csv,
    )

    paths = phase1_paths(workspace)

    assert workspace.manual_validation_csv == manual_validation_csv
    assert "manual_validation" not in paths


def test_write_all_phase1_artifacts_writes_into_run_workspace(tmp_path: Path) -> None:
    from src.pipeline_runner import write_all_phase1_artifacts

    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-a",
        manual_validation_csv=tmp_path / "validation" / "manual_validation.csv",
    ).ensure_directories()

    panel = _minimal_panel()
    paths = write_all_phase1_artifacts(
        workspace=workspace,
        panel=panel,
        features=panel.copy(),
        anomalies=pd.DataFrame(),
        report_markdown="# Report\n",
    )

    assert paths["panel"] == (workspace.processed_dir / "panel.csv").resolve()
    assert paths["features"] == (workspace.processed_dir / "features.csv").resolve()
    assert paths["anomalies"] == (workspace.artifacts_dir / "anomalies.csv").resolve()
    assert paths["report"] == (workspace.artifacts_dir / "report.md").resolve()


def test_load_panel_uses_workspace_processed_path_and_legacy_is_opt_in(tmp_path: Path) -> None:
    from src.manual_validation import load_panel

    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-a",
        manual_validation_csv=tmp_path / "validation" / "manual_validation.csv",
    ).ensure_directories()
    panel = _minimal_panel()
    panel_path = workspace.processed_dir / "panel.csv"
    panel.to_csv(panel_path, index=False)

    loaded = load_panel(workspace=workspace)
    pd.testing.assert_frame_equal(loaded, panel)

    with pytest.raises(ValueError):
        load_panel()

    legacy_panel_path = tmp_path / "legacy" / "processed" / "panel.csv"
    legacy_panel_path.parent.mkdir(parents=True, exist_ok=True)
    panel.to_csv(legacy_panel_path, index=False)

    original_processed = config.DATA_PROCESSED
    config.DATA_PROCESSED = legacy_panel_path.parent
    try:
        legacy_loaded = load_panel(use_legacy_shared_paths=True)
    finally:
        config.DATA_PROCESSED = original_processed

    pd.testing.assert_frame_equal(legacy_loaded, panel)


def test_run_workspace_payload_round_trip(tmp_path: Path) -> None:
    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-123",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    )
    payload = RunWorkspacePayload(
        run_scoped_id=workspace.run_scoped_id,
        root=str(workspace.root),
        processed_dir=str(workspace.processed_dir),
        artifacts_dir=str(workspace.artifacts_dir),
        manual_validation_csv=str(workspace.manual_validation_csv),
        use_legacy_shared_paths=workspace.use_legacy_shared_paths,
    )

    request = ExecutionRequest(
        run_id="run-123",
        request=OrchestrationInput(
            tickers=["AAPL"],
            analysis_goal="find unusual financial changes",
        ),
        plan=OrchestrationPlan(
            steps=[
                PlannedStep(
                    tool_name="run_pipeline",
                    tool_input={},
                    order=0,
                    label="run_pipeline",
                )
            ]
        ),
        interpreted_goal=InterpretedGoal(
            code=InterpretedGoalCode.full_pipeline,
            intent=OrchestrationIntent.full_pipeline_run,
            description="full pipeline",
            user_goal_text="find unusual financial changes",
        ),
        context={"run_workspace": payload.model_dump(mode="json")},
    )

    handoff = request.model_dump(mode="json")

    assert set(handoff["context"]["run_workspace"].keys()) == {
        "run_scoped_id",
        "root",
        "processed_dir",
        "artifacts_dir",
        "manual_validation_csv",
        "use_legacy_shared_paths",
    }
