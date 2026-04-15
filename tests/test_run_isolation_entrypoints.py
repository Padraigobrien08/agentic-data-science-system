from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

import main as main_module
from edgar_project import cli
from edgar_project.orchestration.schemas import (
    InterpretedGoal,
    InterpretedGoalCode,
    OrchestrationOutput,
    OrchestrationRunStatus,
)
from edgar_project.run_workspace import build_run_workspace, phase1_paths


def test_cli_and_main_use_run_scoped_workspaces_without_chdir(
    tmp_path,
    capsys,
) -> None:
    workspace = build_run_workspace(
        workspace_root=tmp_path / "data" / "runs",
        run_scoped_id="run-123",
        manual_validation_csv=tmp_path / "validation" / "manual_validation.csv",
    )
    paths = phase1_paths(workspace)

    cli_out = OrchestrationOutput(
        status=OrchestrationRunStatus.success,
        message="ok",
        interpreted_goal=InterpretedGoal(
            code=InterpretedGoalCode.full_pipeline,
            description="d",
            user_goal_text="find unusual financial changes",
        ),
        run_id="run-123",
        artifact_paths={
            "panel_csv": str(paths["panel"]),
            "features_csv": str(paths["features"]),
            "report_md": str(paths["report"]),
        },
    )

    panel = pd.DataFrame([{"cik": 320193, "period": "2021-Q1", "revenue": 1.0}])
    feats = panel.copy()
    anom = pd.DataFrame([{"cik": 320193, "period": "2021-Q1", "metric": "revenue", "value": 1.0, "zscore": 3.0}])
    dq_df = pd.DataFrame([{"category": "stage_count", "name": "rows", "value": 1, "unit": "rows", "notes": ""}])
    excl_df = pd.DataFrame([{"stage": "metric_extraction", "reason_code": "none", "count": 0, "cik": "", "period": "", "metric": "", "tag": "", "detail": ""}])
    peer_df = pd.DataFrame([{"cik": 320193, "period": "2021-Q1", "metric": "revenue", "peer_alert": "none"}])
    cave_long = pd.DataFrame()

    captured_workspace: dict[str, object] = {}

    def _fake_run_pipeline(*_args, **kwargs):
        captured_workspace["run_pipeline_workspace"] = kwargs.get("workspace")
        return panel, feats, anom, "# report\n", dq_df, excl_df, peer_df, cave_long

    def _fake_write_all(*_args, **kwargs):
        captured_workspace["write_workspace"] = kwargs.get("workspace")
        return paths

    with patch("os.chdir") as mock_chdir:
        with patch.object(cli, "run_analysis_agent", return_value=cli_out):
            assert cli.main(["run", "--tickers", "AAPL", "--goal", "find unusual financial changes"]) == 0
        cli_stdout = capsys.readouterr().out
        assert "data/runs/<run_scoped_id>/processed" in cli_stdout
        assert "data/runs/<run_scoped_id>/artifacts" in cli_stdout

        with patch.object(main_module, "uuid4", return_value=SimpleNamespace(hex="run1234567890abcdef")):
            with patch.object(main_module.config, "DATA_RUNS", workspace.root.parent):
                with patch.object(main_module, "run_pipeline_computation", side_effect=_fake_run_pipeline):
                    with patch.object(main_module, "write_all_phase1_artifacts", side_effect=_fake_write_all):
                        main_module.main()

        main_stdout = capsys.readouterr().out
        assert "Run workspace:" in main_stdout
        assert "/data/runs/" in main_stdout or str(workspace.root) in main_stdout
        assert "data/processed" not in main_stdout
        assert "data/artifacts" not in main_stdout
        assert captured_workspace["run_pipeline_workspace"].run_scoped_id == "main-run123456789"
        assert captured_workspace["write_workspace"].run_scoped_id == "main-run123456789"
        mock_chdir.assert_not_called()
