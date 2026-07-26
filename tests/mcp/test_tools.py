"""MCP tool functions: envelopes, mocks, error vs no_data."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import requests

from edgar_project.mcp import tools as mcp_tools
from edgar_project.mcp.schemas import (
    ARTIFACT_KEY_ANOMALIES,
    ARTIFACT_KEY_DATA_QUALITY,
    ARTIFACT_KEY_EXCLUSIONS,
    ARTIFACT_KEY_FEATURES,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC,
    ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD,
    ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION,
    ARTIFACT_KEY_METRIC_CAVEATS_PANEL,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY,
    ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD,
    ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY,
    ARTIFACT_KEY_PANEL,
    ARTIFACT_KEY_PEER_SIGNALS,
    ARTIFACT_KEY_REPORT,
    ARTIFACT_KEY_TREND_BREAKS,
    ARTIFACT_KEY_UNIFIED_FINDINGS,
    CODE_SEC_FETCH,
    CODE_UNKNOWN_TICKER,
    BuildPanelInput,
    ComputeFeaturesInput,
    FetchCompanyDataInput,
    GenerateReportInput,
    ResolveCompanyInput,
    RunPipelineInput,
    ToolResponseEnvelope,
    ToolStatus,
)
from edgar_project.orchestration.schemas import RunWorkspacePayload


def assert_envelope_shape(env: ToolResponseEnvelope) -> None:
    d = env.model_dump(mode="json")
    assert d["status"] in ("success", "no_data", "error")
    assert "message" in d
    assert isinstance(d["data"], dict)
    assert isinstance(d["artifacts"], dict)
    assert isinstance(d["errors"], list)
    if d["status"] == "error":
        assert len(d["errors"]) >= 1
        assert all("code" in e and "message" in e for e in d["errors"])
    else:
        assert d["errors"] == []


def test_resolve_company_mocked_known_ticker() -> None:
    fake = {
        "ticker": "AAPL",
        "cik": 320193,
        "company_name": "Apple Inc.",
    }
    with patch.object(mcp_tools.ad, "resolve_company_dict", return_value=fake):
        env = mcp_tools.resolve_company_tool(ResolveCompanyInput(ticker="AAPL"))
    assert_envelope_shape(env)
    assert env.status == ToolStatus.success
    assert env.data["cik"] == 320193
    assert env.data["provenance"]["ciks"] == [320193]


def test_resolve_company_unknown_ticker_error() -> None:
    with patch.object(
        mcp_tools.ad,
        "resolve_company_dict",
        side_effect=ValueError("unknown ticker"),
    ):
        env = mcp_tools.resolve_company_tool(ResolveCompanyInput(ticker="ZZZZ"))
    assert env.status == ToolStatus.error
    assert env.errors[0].code == CODE_UNKNOWN_TICKER
    assert_envelope_shape(env)


def test_run_pipeline_mocked_artifact_keys(
    sample_panel_row: pd.DataFrame,
    tmp_artifact_paths: dict[str, Path],
) -> None:
    feats = sample_panel_row.copy()
    anom = pd.DataFrame(
        {
            "cik": [320193],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "value": [1.0],
            "zscore": [3.0],
        }
    )
    md = "# report\n"
    dq_df = pd.DataFrame(
        [{"category": "stage_count", "name": "panel_rows_after_revenue_required", "value": 1, "unit": "rows", "notes": ""}]
    )
    ex_df = pd.DataFrame(
        [
            {
                "stage": "metric_extraction",
                "reason_code": "unsupported_unit",
                "count": 1,
                "cik": "",
                "period": "",
                "metric": "",
                "tag": "",
                "detail": "",
            }
        ]
    )
    peer_df = pd.DataFrame(
        [{"cik": 1, "period": "2021-Q1", "metric": "revenue", "peer_alert": "none"}]
    )
    prov = [
        {"ticker": "AAPL", "cik": 320193},
    ]

    with patch.object(mcp_tools.ad, "ticker_cik_pairs", return_value=prov):
        with patch.object(
            mcp_tools.ad,
            "run_full_pipeline",
            return_value=(sample_panel_row, feats, anom, md, dq_df, ex_df, peer_df, pd.DataFrame()),
        ):
            with patch.object(
                mcp_tools.ad,
                "write_all_phase1_artifacts",
                return_value=tmp_artifact_paths,
            ):
                with patch.object(mcp_tools.ad, "anomaly_detection_params", return_value={}):
                    with patch.object(mcp_tools.ad, "peer_signal_params", return_value={}):
                        env = mcp_tools.run_pipeline_tool(
                            RunPipelineInput(tickers=["AAPL"], refresh=False)
                        )

    assert_envelope_shape(env)
    assert env.status == ToolStatus.success
    art = env.artifacts
    assert ARTIFACT_KEY_PANEL in art
    assert ARTIFACT_KEY_FEATURES in art
    assert ARTIFACT_KEY_ANOMALIES in art
    assert ARTIFACT_KEY_REPORT in art
    assert ARTIFACT_KEY_DATA_QUALITY in art
    assert ARTIFACT_KEY_EXCLUSIONS in art
    assert ARTIFACT_KEY_PEER_SIGNALS in art
    assert ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY in art
    assert ARTIFACT_KEY_METRIC_COVERAGE_BY_COMPANY in art
    assert ARTIFACT_KEY_METRIC_COVERAGE_BY_PERIOD in art
    assert ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION in art
    assert ARTIFACT_KEY_METRIC_CAVEATS_PANEL in art
    assert ARTIFACT_KEY_TREND_BREAKS in art
    assert ARTIFACT_KEY_UNIFIED_FINDINGS in art
    assert ARTIFACT_KEY_FINDINGS_SUMMARY_BY_COMPANY in art
    assert ARTIFACT_KEY_FINDINGS_SUMMARY_BY_METRIC in art
    assert ARTIFACT_KEY_FINDINGS_SUMMARY_BY_PERIOD in art
    assert str(tmp_artifact_paths["panel"]) in art[ARTIFACT_KEY_PANEL]
    assert "artifacts_detail" in env.data
    assert "trustworthiness_artifact_paths" in env.data
    assert "unified_findings_path" in env.data
    assert "findings_summary_by_company_path" in env.data
    assert "findings_summary_by_metric_path" in env.data
    assert "findings_summary_by_period_path" in env.data
    assert "combined_findings_count" in env.data


def test_build_panel_no_data_empty_panel() -> None:
    empty = pd.DataFrame()
    prov = [{"ticker": "AAPL", "cik": 320193}]
    with patch.object(mcp_tools.ad, "build_panel_dataframe", return_value=empty):
        with patch.object(mcp_tools.ad, "ticker_cik_pairs", return_value=prov):
            env = mcp_tools.build_panel_tool(
                BuildPanelInput(tickers=["AAPL"], refresh=False)
            )
    assert env.status == ToolStatus.no_data
    assert env.errors == []
    assert_envelope_shape(env)


def test_run_pipeline_no_data_empty_panel_distinct_from_error(
    sample_panel_row: pd.DataFrame,
) -> None:
    """no_data: empty panel, no exception. error: ValueError from pipeline."""
    empty = pd.DataFrame()
    prov = [{"ticker": "AAPL", "cik": 320193}]
    with patch.object(mcp_tools.ad, "ticker_cik_pairs", return_value=prov):
        with patch.object(
            mcp_tools.ad,
            "run_full_pipeline",
            return_value=(empty, empty, empty, "", pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()),
        ):
            with patch.object(mcp_tools.ad, "anomaly_detection_params", return_value={}):
                nd = mcp_tools.run_pipeline_tool(
                    RunPipelineInput(tickers=["AAPL"], refresh=False)
                )
    assert nd.status == ToolStatus.no_data
    assert nd.errors == []

    with patch.object(
        mcp_tools.ad,
        "run_full_pipeline",
        side_effect=ValueError("bad ticker"),
    ):
        err = mcp_tools.run_pipeline_tool(
            RunPipelineInput(tickers=["AAPL"], refresh=False)
        )
    assert err.status == ToolStatus.error
    assert err.errors[0].code == CODE_UNKNOWN_TICKER
    assert nd.status != err.status


def test_fetch_company_data_connection_error_uses_sec_code() -> None:
    with patch.object(
        mcp_tools.ad,
        "fetch_company_data_dict",
        side_effect=requests.ConnectionError("refused"),
    ):
        env = mcp_tools.fetch_company_data_tool(
            FetchCompanyDataInput(ticker="AAPL", refresh=True)
        )
    assert env.status == ToolStatus.error
    assert env.errors[0].code == CODE_SEC_FETCH
    assert env.errors[0].http_status is None
    assert_envelope_shape(env)


def test_fetch_company_data_http_error_structured() -> None:
    resp = MagicMock()
    resp.status_code = 403
    http_exc = requests.HTTPError("403", response=resp)
    with patch.object(
        mcp_tools.ad,
        "fetch_company_data_dict",
        side_effect=http_exc,
    ):
        env = mcp_tools.fetch_company_data_tool(
            FetchCompanyDataInput(ticker="AAPL", refresh=True)
        )
    assert env.status == ToolStatus.error
    assert env.errors[0].http_status == 403
    assert_envelope_shape(env)


def test_compute_features_value_error_from_panel_build_is_unknown_ticker() -> None:
    """Phase 1 raises ValueError for unknown ticker; align with build_panel."""
    with patch.object(
        mcp_tools.ad,
        "build_panel_dataframe",
        side_effect=ValueError("unknown ticker ZZZZ"),
    ):
        env = mcp_tools.compute_features_tool(
            ComputeFeaturesInput(tickers=["ZZZZ"], panel_csv_path=None)
        )
    assert env.status == ToolStatus.error
    assert env.errors[0].code == CODE_UNKNOWN_TICKER


def test_generate_report_default_paths_includes_trustworthiness(
    sample_panel_row: pd.DataFrame,
    tmp_artifact_paths: dict[str, Path],
) -> None:
    anom = pd.DataFrame(
        {
            "cik": [320193],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "value": [1.0],
            "zscore": [3.0],
        }
    )
    out_report = tmp_artifact_paths["report"].parent / "written_report.md"
    peer_df = pd.DataFrame(
        [{"cik": 1, "period": "2021-Q1", "metric": "revenue", "peer_alert": "none"}]
    )
    with patch.object(mcp_tools.ad, "phase1_paths", return_value=tmp_artifact_paths):
        with patch.object(mcp_tools.ad, "read_features_csv", return_value=sample_panel_row):
            with patch.object(mcp_tools.ad, "read_anomalies_csv", return_value=anom):
                with patch.object(mcp_tools.ad, "read_peer_signals_csv", return_value=peer_df):
                    with patch.object(mcp_tools.ad, "generate_report_markdown", return_value="# r\n"):
                        with patch.object(mcp_tools.ad, "write_report_md", return_value=out_report):
                            with patch.object(mcp_tools.ad, "sorted_unique_ciks", return_value=[320193]):
                                env = mcp_tools.generate_report_tool(
                                    GenerateReportInput(use_default_artifact_paths=True)
                                )
    assert_envelope_shape(env)
    assert env.status == ToolStatus.success
    assert ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY in env.artifacts
    assert ARTIFACT_KEY_METRIC_CAVEATS_EXTRACTION in env.artifacts
    assert ARTIFACT_KEY_METRIC_CAVEATS_PANEL in env.artifacts
    assert ARTIFACT_KEY_METRIC_COVERAGE_SUMMARY in env.data["trustworthiness_artifact_paths"]
    assert "trustworthiness_summary" in env.data


def test_generate_report_tool_uses_workspace_payload_for_normal_mode(
    sample_panel_row: pd.DataFrame,
    tmp_artifact_paths: dict[str, Path],
) -> None:
    workspace = RunWorkspacePayload(
        run_scoped_id="run-123",
        root="/runs/run-123",
        processed_dir="/runs/run-123/processed",
        artifacts_dir="/runs/run-123/artifacts",
        manual_validation_csv="/repo/validation/manual_validation.csv",
        use_legacy_shared_paths=False,
    )
    anom = pd.DataFrame(
        {
            "cik": [320193],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "value": [1.0],
            "zscore": [3.0],
        }
    )
    out_report = tmp_artifact_paths["report"].parent / "workspace_report.md"
    with patch.object(mcp_tools.ad, "read_features_csv", return_value=sample_panel_row):
        with patch.object(mcp_tools.ad, "read_anomalies_csv", return_value=anom):
            with patch.object(mcp_tools.ad, "generate_report_markdown", return_value="# r\n") as mock_generate:
                with patch.object(mcp_tools.ad, "write_report_md", return_value=out_report) as mock_write:
                    with patch.object(mcp_tools.ad, "sorted_unique_ciks", return_value=[320193]):
                        env = mcp_tools.generate_report_tool(
                            GenerateReportInput(
                                features_csv_path="/runs/run-123/processed/features.csv",
                                anomalies_csv_path="/runs/run-123/artifacts/anomalies.csv",
                                run_workspace=workspace,
                            )
                        )
    assert_envelope_shape(env)
    assert env.status == ToolStatus.success
    report_workspace = mock_generate.call_args.kwargs["workspace"]
    assert report_workspace.run_scoped_id == "run-123"
    assert report_workspace.manual_validation_csv.as_posix() == "/repo/validation/manual_validation.csv"
    assert mock_write.call_args.kwargs["workspace"].run_scoped_id == "run-123"


def test_run_pipeline_and_generate_report_inputs_accept_run_workspace_payload() -> None:
    workspace = RunWorkspacePayload(
        run_scoped_id="run-123",
        root="/runs/run-123",
        processed_dir="/runs/run-123/processed",
        artifacts_dir="/runs/run-123/artifacts",
        manual_validation_csv="/repo/validation/manual_validation.csv",
        use_legacy_shared_paths=False,
    )

    run_input = RunPipelineInput(tickers=["AAPL"], refresh=False, run_workspace=workspace)
    report_input = GenerateReportInput(
        features_csv_path="/runs/run-123/processed/features.csv",
        anomalies_csv_path="/runs/run-123/artifacts/anomalies.csv",
        run_workspace=workspace,
    )

    assert run_input.run_workspace is not None
    assert run_input.run_workspace.run_scoped_id == "run-123"
    assert report_input.run_workspace is not None
    assert report_input.run_workspace.artifacts_dir == "/runs/run-123/artifacts"


def test_run_pipeline_tool_passes_workspace_to_pipeline_and_writer_contract(
    sample_panel_row: pd.DataFrame,
    tmp_artifact_paths: dict[str, Path],
) -> None:
    workspace = RunWorkspacePayload(
        run_scoped_id="run-123",
        root="/runs/run-123",
        processed_dir="/runs/run-123/processed",
        artifacts_dir="/runs/run-123/artifacts",
        manual_validation_csv="/repo/validation/manual_validation.csv",
        use_legacy_shared_paths=False,
    )
    feats = sample_panel_row.copy()
    anom = pd.DataFrame(
        {
            "cik": [320193],
            "period": ["2021-Q1"],
            "metric": ["revenue"],
            "value": [1.0],
            "zscore": [3.0],
        }
    )
    dq_df = pd.DataFrame(
        [{"category": "stage_count", "name": "panel_rows_after_revenue_required", "value": 1, "unit": "rows", "notes": ""}]
    )
    ex_df = pd.DataFrame(
        [
            {
                "stage": "metric_extraction",
                "reason_code": "unsupported_unit",
                "count": 1,
                "cik": "",
                "period": "",
                "metric": "",
                "tag": "",
                "detail": "",
            }
        ]
    )
    peer_df = pd.DataFrame(
        [{"cik": 1, "period": "2021-Q1", "metric": "revenue", "peer_alert": "none"}]
    )
    prov = [{"ticker": "AAPL", "cik": 320193}]

    with patch.object(mcp_tools.ad, "ticker_cik_pairs", return_value=prov):
        with patch.object(
            mcp_tools.ad,
            "run_full_pipeline",
            return_value=(sample_panel_row, feats, anom, "# report\n", dq_df, ex_df, peer_df, pd.DataFrame()),
        ) as mock_run:
            with patch.object(
                mcp_tools.ad,
                "write_all_phase1_artifacts",
                return_value=tmp_artifact_paths,
            ) as mock_write:
                with patch.object(mcp_tools.ad, "anomaly_detection_params", return_value={}):
                    with patch.object(mcp_tools.ad, "peer_signal_params", return_value={}):
                        env = mcp_tools.run_pipeline_tool(
                            RunPipelineInput(
                                tickers=["AAPL"],
                                refresh=False,
                                run_workspace=workspace,
                            )
                        )
    assert_envelope_shape(env)
    assert env.status == ToolStatus.success
    assert mock_run.call_args.kwargs["workspace"].run_scoped_id == "run-123"
    assert mock_write.call_args.kwargs["workspace"].run_scoped_id == "run-123"


def test_to_json_dict_serializes_envelope() -> None:
    fake = {"ticker": "AAPL", "cik": 320193, "company_name": "Apple Inc."}
    with patch.object(mcp_tools.ad, "resolve_company_dict", return_value=fake):
        env = mcp_tools.resolve_company_tool(ResolveCompanyInput(ticker="AAPL"))
    out = mcp_tools.to_json_dict(env)
    assert out["status"] == "success"
    assert "data" in out and "errors" in out
