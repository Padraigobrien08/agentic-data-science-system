"""Contract tests for run-scoped workspaces."""

from __future__ import annotations

from pathlib import Path

import config

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


def test_phase1_paths_are_run_scoped(tmp_path: Path) -> None:
    workspace = build_run_workspace(
        workspace_root=tmp_path / "workspaces",
        run_scoped_id="run-123",
        manual_validation_csv=Path("/repo/validation/manual_validation.csv"),
    )

    paths = phase1_paths(workspace)

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
