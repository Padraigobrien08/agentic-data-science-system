"""
MCP tool implementations — thin wrappers mapping inputs/outputs to Pydantic models.

All pipeline behavior lives in ``src.*`` and ``src.pipeline_runner``; this module only
calls :mod:`edgar_project.mcp.adapters` and maps exceptions to :class:`ToolStatus`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
from pydantic import BaseModel

from edgar_project.mcp import adapters as ad
from edgar_project.mcp.schemas import (
    ArtifactPaths,
    BuildPanelInput,
    BuildPanelOutput,
    ComputeFeaturesInput,
    ComputeFeaturesOutput,
    DetectAnomaliesInput,
    DetectAnomaliesOutput,
    ErrorInfo,
    FetchCompanyDataInput,
    FetchCompanyDataOutput,
    GenerateReportInput,
    GenerateReportOutput,
    PipelineSummaryCounts,
    ResolveCompanyInput,
    ResolveCompanyOutput,
    RunPipelineInput,
    RunPipelineOutput,
    ToolStatus,
)

ad.ensure_sys_path()

E_UNKNOWN_TICKER = "UNKNOWN_TICKER"
E_SEC_FETCH = "SEC_FETCH_ERROR"
E_VALIDATION = "VALIDATION_ERROR"
E_FILE_NOT_FOUND = "FILE_NOT_FOUND"
E_INTERNAL = "INTERNAL_ERROR"


def _err_out(
    model: type[Any],
    *,
    code: str,
    message: str,
    detail: str | None = None,
) -> Any:
    return model(
        status=ToolStatus.error,
        message=message,
        error=ErrorInfo(code=code, message=message, detail=detail),
    )


def _no_data_out(model: type[Any], message: str, **fields: Any) -> Any:
    return model(status=ToolStatus.no_data, message=message, **fields)


def resolve_company_tool(inp: ResolveCompanyInput) -> ResolveCompanyOutput:
    try:
        r = ad.resolve_company_dict(inp.ticker)
        return ResolveCompanyOutput(
            status=ToolStatus.success,
            ticker=r["ticker"],
            cik=r["cik"],
            company_name=r.get("company_name"),
        )
    except ValueError as e:
        return _err_out(
            ResolveCompanyOutput,
            code=E_UNKNOWN_TICKER,
            message=str(e),
            detail=str(e),
        )
    except Exception as e:
        return _err_out(
            ResolveCompanyOutput,
            code=E_INTERNAL,
            message="resolve_company failed",
            detail=str(e),
        )


def fetch_company_data_tool(inp: FetchCompanyDataInput) -> FetchCompanyDataOutput:
    try:
        d = ad.fetch_company_data_dict(inp.ticker, refresh=inp.refresh)
        paths = ad.cache_paths_from_fetch_result(d)
        return FetchCompanyDataOutput(
            status=ToolStatus.success,
            ticker=d["ticker"],
            cik=int(d["cik"]),
            cache_paths=paths,
        )
    except ValueError as e:
        return _err_out(
            FetchCompanyDataOutput,
            code=E_UNKNOWN_TICKER,
            message=str(e),
            detail=str(e),
        )
    except requests.HTTPError as e:
        return _err_out(
            FetchCompanyDataOutput,
            code=E_SEC_FETCH,
            message=f"SEC HTTP error: {e.response.status_code if e.response else 'unknown'}",
            detail=str(e),
        )
    except Exception as e:
        return _err_out(
            FetchCompanyDataOutput,
            code=E_INTERNAL,
            message="fetch_company_data failed",
            detail=str(e),
        )


def build_panel_tool(inp: BuildPanelInput) -> BuildPanelOutput:
    tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
    if not tickers:
        return _err_out(
            BuildPanelOutput,
            code=E_VALIDATION,
            message="tickers list is empty after normalization",
        )
    if len(tickers) > 5:
        return _err_out(BuildPanelOutput, code=E_VALIDATION, message="At most 5 tickers allowed")
    try:
        panel = ad.build_panel_dataframe(tickers, refresh=inp.refresh)
        if panel.empty:
            return _no_data_out(
                BuildPanelOutput,
                "Panel has no rows (no extractable metrics for these tickers/periods).",
                panel_csv_path=None,
                row_count=0,
                columns=[],
            )
        path = ad.write_panel_csv(panel)
        cols = [str(c) for c in panel.columns]
        return BuildPanelOutput(
            status=ToolStatus.success,
            panel_csv_path=str(path),
            row_count=len(panel),
            columns=cols,
        )
    except ValueError as e:
        return _err_out(BuildPanelOutput, code=E_UNKNOWN_TICKER, message=str(e), detail=str(e))
    except requests.HTTPError as e:
        return _err_out(
            BuildPanelOutput,
            code=E_SEC_FETCH,
            message=f"SEC HTTP error: {e.response.status_code if e.response else 'unknown'}",
            detail=str(e),
        )
    except Exception as e:
        return _err_out(
            BuildPanelOutput,
            code=E_INTERNAL,
            message="build_panel failed",
            detail=str(e),
        )


def compute_features_tool(inp: ComputeFeaturesInput) -> ComputeFeaturesOutput:
    try:
        if inp.panel_csv_path:
            panel = ad.read_panel_csv(Path(inp.panel_csv_path).expanduser().resolve())
        else:
            assert inp.tickers is not None
            tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
            panel = ad.build_panel_dataframe(tickers, refresh=False)
        if panel.empty:
            return _no_data_out(
                ComputeFeaturesOutput,
                "Panel is empty; cannot compute features.",
                features_csv_path=None,
                row_count=0,
                columns=[],
            )
        feats = ad.compute_features_dataframe(panel)
        path = ad.write_features_csv(feats)
        cols = [str(c) for c in feats.columns]
        return ComputeFeaturesOutput(
            status=ToolStatus.success,
            features_csv_path=str(path),
            row_count=len(feats),
            columns=cols,
        )
    except FileNotFoundError as e:
        return _err_out(
            ComputeFeaturesOutput,
            code=E_FILE_NOT_FOUND,
            message=str(e),
            detail=str(e),
        )
    except ValueError as e:
        return _err_out(ComputeFeaturesOutput, code=E_VALIDATION, message=str(e), detail=str(e))
    except requests.HTTPError as e:
        return _err_out(
            ComputeFeaturesOutput,
            code=E_SEC_FETCH,
            message=f"SEC HTTP error: {e.response.status_code if e.response else 'unknown'}",
            detail=str(e),
        )
    except Exception as e:
        return _err_out(
            ComputeFeaturesOutput,
            code=E_INTERNAL,
            message="compute_features failed",
            detail=str(e),
        )


def detect_anomalies_tool(inp: DetectAnomaliesInput) -> DetectAnomaliesOutput:
    try:
        if inp.features_csv_path:
            feats = ad.read_features_csv(Path(inp.features_csv_path).expanduser().resolve())
        else:
            assert inp.tickers is not None
            tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
            panel = ad.build_panel_dataframe(tickers, refresh=False)
            if panel.empty:
                return _no_data_out(
                    DetectAnomaliesOutput,
                    "Panel empty; no features to score.",
                    anomalies_csv_path=None,
                    anomaly_count=0,
                )
            feats = ad.compute_features_dataframe(panel)
        anom = ad.detect_anomalies_dataframe(feats)
        path = ad.write_anomalies_csv(anom)
        return DetectAnomaliesOutput(
            status=ToolStatus.success,
            anomalies_csv_path=str(path),
            anomaly_count=len(anom),
        )
    except FileNotFoundError as e:
        return _err_out(
            DetectAnomaliesOutput,
            code=E_FILE_NOT_FOUND,
            message=str(e),
            detail=str(e),
        )
    except ValueError as e:
        return _err_out(DetectAnomaliesOutput, code=E_VALIDATION, message=str(e), detail=str(e))
    except requests.HTTPError as e:
        return _err_out(
            DetectAnomaliesOutput,
            code=E_SEC_FETCH,
            message=f"SEC HTTP error: {e.response.status_code if e.response else 'unknown'}",
            detail=str(e),
        )
    except Exception as e:
        return _err_out(
            DetectAnomaliesOutput,
            code=E_INTERNAL,
            message="detect_anomalies failed",
            detail=str(e),
        )


def generate_report_tool(inp: GenerateReportInput) -> GenerateReportOutput:
    try:
        if inp.use_default_artifact_paths:
            ap = ad.phase1_paths()
            feats = ad.read_features_csv(ap["features"])
            anom = ad.read_anomalies_csv(ap["anomalies"])
        else:
            assert inp.features_csv_path and inp.anomalies_csv_path
            feats = ad.read_features_csv(Path(inp.features_csv_path).expanduser().resolve())
            anom = ad.read_anomalies_csv(Path(inp.anomalies_csv_path).expanduser().resolve())
        if feats.empty:
            return _no_data_out(GenerateReportOutput, "Features dataframe is empty.", report_md_path=None)
        md = ad.generate_report_markdown(anom, feats)
        path = ad.write_report_md(md)
        return GenerateReportOutput(status=ToolStatus.success, report_md_path=str(path))
    except FileNotFoundError as e:
        return _err_out(
            GenerateReportOutput,
            code=E_FILE_NOT_FOUND,
            message=str(e),
            detail=str(e),
        )
    except ValueError as e:
        return _err_out(GenerateReportOutput, code=E_VALIDATION, message=str(e), detail=str(e))
    except Exception as e:
        return _err_out(
            GenerateReportOutput,
            code=E_INTERNAL,
            message="generate_report failed",
            detail=str(e),
        )


def run_pipeline_tool(inp: RunPipelineInput) -> RunPipelineOutput:
    tickers = [t.strip().upper() for t in (inp.tickers or []) if t.strip()]
    if not tickers:
        import config

        tickers = list(config.DEFAULT_TICKERS[:5])
    if len(tickers) > 5:
        return _err_out(RunPipelineOutput, code=E_VALIDATION, message="At most 5 tickers allowed")

    try:
        panel, feats, anom, md = ad.run_full_pipeline(tickers, refresh=inp.refresh)
        if panel.empty:
            ap = ad.phase1_paths()
            return RunPipelineOutput(
                status=ToolStatus.no_data,
                message="Pipeline produced an empty panel (no rows after extraction).",
                artifacts=ArtifactPaths(
                    panel_csv=str(ap["panel"]),
                    features_csv=str(ap["features"]),
                    anomalies_csv=str(ap["anomalies"]),
                    report_md=str(ap["report"]),
                ),
                counts=PipelineSummaryCounts(),
            )
        paths = ad.write_all_phase1_artifacts(panel, feats, anom, md)
        arts = ArtifactPaths(
            panel_csv=str(paths["panel"]),
            features_csv=str(paths["features"]),
            anomalies_csv=str(paths["anomalies"]),
            report_md=str(paths["report"]),
        )
        return RunPipelineOutput(
            status=ToolStatus.success,
            artifacts=arts,
            counts=PipelineSummaryCounts(
                panel_rows=len(panel),
                feature_rows=len(feats),
                anomaly_rows=len(anom),
            ),
        )
    except ValueError as e:
        return _err_out(RunPipelineOutput, code=E_UNKNOWN_TICKER, message=str(e), detail=str(e))
    except requests.HTTPError as e:
        return _err_out(
            RunPipelineOutput,
            code=E_SEC_FETCH,
            message=f"SEC HTTP error: {e.response.status_code if e.response else 'unknown'}",
            detail=str(e),
        )
    except Exception as e:
        return _err_out(
            RunPipelineOutput,
            code=E_INTERNAL,
            message="run_pipeline failed",
            detail=str(e),
        )


def to_json_dict(model: BaseModel) -> dict[str, Any]:
    return model.model_dump(mode="json")
