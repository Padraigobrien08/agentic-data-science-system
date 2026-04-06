"""
MCP tool implementations for the EDGAR Phase 1 pipeline.

Each function returns a Pydantic output model with :class:`ToolStatus` and optional :class:`ErrorInfo`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import requests
from pydantic import BaseModel

from edgar_project.mcp import pipeline as pl
from edgar_project.mcp.adapters import ensure_sys_path
from edgar_project.mcp.schemas import (
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
    ArtifactPaths,
)

ensure_sys_path()

# --- Error codes (stable) ----------------------------------------------------

E_UNKNOWN_TICKER = "UNKNOWN_TICKER"
E_SEC_FETCH = "SEC_FETCH_ERROR"
E_VALIDATION = "VALIDATION_ERROR"
E_EMPTY_PANEL = "EMPTY_PANEL"
E_FILE_NOT_FOUND = "FILE_NOT_FOUND"
E_IO = "IO_ERROR"
E_INTERNAL = "INTERNAL_ERROR"


def _err_out(
    model: type[Any],
    *,
    code: str,
    message: str,
    detail: str | None = None,
) -> Any:
    """Build a typed error response (all tool-specific fields None)."""
    return model(
        status=ToolStatus.error,
        message=message,
        error=ErrorInfo(code=code, message=message, detail=detail),
    )


def _no_data_out(model: type[Any], message: str, **fields: Any) -> Any:
    return model(status=ToolStatus.no_data, message=message, **fields)


# --- 1. resolve_company -------------------------------------------------------

def resolve_company_tool(inp: ResolveCompanyInput) -> ResolveCompanyOutput:
    try:
        from src.data_fetch import resolve_company

        r = resolve_company(inp.ticker.strip())
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


# --- 2. fetch_company_data --------------------------------------------------

def fetch_company_data_tool(inp: FetchCompanyDataInput) -> FetchCompanyDataOutput:
    try:
        from src.data_fetch import get_company_data

        d = get_company_data(inp.ticker.strip(), refresh=inp.refresh)
        cik10 = d["cik10"]
        ticker_u = d["ticker"]
        import config

        tdir = config.DATA_RAW / ticker_u
        sub = tdir / f"CIK{cik10}_submissions.json"
        fac = tdir / f"CIK{cik10}_companyfacts.json"
        paths = {
            "submissions": str(sub.resolve()),
            "companyfacts": str(fac.resolve()),
        }
        return FetchCompanyDataOutput(
            status=ToolStatus.success,
            ticker=ticker_u,
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


# --- 3. build_panel -----------------------------------------------------------

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
        panel = pl.build_panel_dataframe(tickers, refresh=inp.refresh)
        if panel.empty:
            return _no_data_out(
                BuildPanelOutput,
                "Panel has no rows (no extractable metrics for these tickers/periods).",
                panel_csv_path=None,
                row_count=0,
                columns=[],
            )
        path = pl.write_panel_csv(panel)
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


# --- 4. compute_features ------------------------------------------------------

def compute_features_tool(inp: ComputeFeaturesInput) -> ComputeFeaturesOutput:
    try:
        if inp.panel_csv_path:
            panel = pl.read_panel_csv(Path(inp.panel_csv_path).expanduser().resolve())
        else:
            assert inp.tickers is not None
            tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
            panel = pl.build_panel_dataframe(tickers, refresh=False)
        if panel.empty:
            return _no_data_out(
                ComputeFeaturesOutput,
                "Panel is empty; cannot compute features.",
                features_csv_path=None,
                row_count=0,
                columns=[],
            )
        feats = pl.compute_features_dataframe(panel)
        path = pl.write_features_csv(feats)
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


# --- 5. detect_anomalies ----------------------------------------------------

def detect_anomalies_tool(inp: DetectAnomaliesInput) -> DetectAnomaliesOutput:
    try:
        if inp.features_csv_path:
            feats = pl.read_features_csv(Path(inp.features_csv_path).expanduser().resolve())
        else:
            assert inp.tickers is not None
            tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
            panel = pl.build_panel_dataframe(tickers, refresh=False)
            if panel.empty:
                return _no_data_out(
                    DetectAnomaliesOutput,
                    "Panel empty; no features to score.",
                    anomalies_csv_path=None,
                    anomaly_count=0,
                )
            feats = pl.compute_features_dataframe(panel)
        anom = pl.detect_anomalies_dataframe(feats)
        path = pl.write_anomalies_csv(anom)
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


# --- 6. generate_report -------------------------------------------------------

def generate_report_tool(inp: GenerateReportInput) -> GenerateReportOutput:
    ensure_sys_path()
    import config
    from src.report import generate_report

    try:
        if inp.use_default_artifact_paths:
            ap = pl.artifact_paths_dict()
            feats = pl.read_features_csv(ap["features"])
            anom = pl.read_anomalies_csv(ap["anomalies"])
        else:
            assert inp.features_csv_path and inp.anomalies_csv_path
            feats = pl.read_features_csv(Path(inp.features_csv_path).expanduser().resolve())
            anom = pl.read_anomalies_csv(Path(inp.anomalies_csv_path).expanduser().resolve())
        if feats.empty:
            return _no_data_out(GenerateReportOutput, "Features dataframe is empty.", report_md_path=None)
        md = generate_report(anom, feats, top_n=5)
        path = pl.write_report_md(md)
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


# --- 7. run_pipeline ----------------------------------------------------------

def run_pipeline_tool(inp: RunPipelineInput) -> RunPipelineOutput:
    ensure_sys_path()
    import config
    from src.report import generate_report

    tickers = [t.strip().upper() for t in inp.tickers if t.strip()]
    if not tickers:
        tickers = list(config.DEFAULT_TICKERS[:5])
    if len(tickers) > 5:
        return _err_out(RunPipelineOutput, code=E_VALIDATION, message="At most 5 tickers allowed")

    try:
        long_frames = []
        from src.data_fetch import get_company_data
        from src.metric_extraction import extract_metrics

        for t in tickers:
            d = get_company_data(t, refresh=inp.refresh)
            long_frames.append(
                extract_metrics(d["facts"], int(d["cik"]), years=config.YEARS_LOOKBACK)
            )
        from src.normalization import build_panel

        panel = build_panel(long_frames)
        if panel.empty:
            ap = pl.artifact_paths_dict()
            return RunPipelineOutput(
                status=ToolStatus.no_data,
                message="Pipeline produced an empty panel (no rows after extraction).",
                artifacts=ArtifactPaths(
                    panel_csv=str(ap["panel"].resolve()),
                    features_csv=str(ap["features"].resolve()),
                    anomalies_csv=str(ap["anomalies"].resolve()),
                    report_md=str(ap["report"].resolve()),
                ),
                counts=PipelineSummaryCounts(),
            )
        from src.features import compute_features
        from src.anomaly import detect_anomalies

        feats = compute_features(panel)
        anom = detect_anomalies(feats)
        md = generate_report(anom, feats, top_n=5)

        pp = pl.write_panel_csv(panel)
        pf = pl.write_features_csv(feats)
        pa = pl.write_anomalies_csv(anom)
        pr = pl.write_report_md(md)

        arts = ArtifactPaths(
            panel_csv=str(pp),
            features_csv=str(pf),
            anomalies_csv=str(pa),
            report_md=str(pr),
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
    """Serialize a tool response for MCP (JSON-safe)."""
    return model.model_dump(mode="json")
