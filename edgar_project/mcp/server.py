"""
MCP stdio server (FastMCP) exposing EDGAR Phase 1 tools.

Run from repository root::

    python -m edgar_project.mcp.server
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

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
    ResolveCompanyInput,
    ResolveCompanyOutput,
    RunPipelineInput,
    RunPipelineOutput,
    ToolStatus,
)
from edgar_project.mcp import tools as mcp_tools

ensure_sys_path()

logger = logging.getLogger(__name__)

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "Install the MCP SDK: pip install 'mcp>=1.0'"
    ) from e

mcp = FastMCP("edgar-anomaly-detector")


def _validation_error_payload(exc: ValidationError, response_cls: type[Any]) -> dict[str, Any]:
    """Map Pydantic validation failure to the unified tool error envelope."""
    err = ErrorInfo(
        code=mcp_tools.E_VALIDATION,
        message="Input validation failed",
        detail=exc.json(),
    )
    base = response_cls(status=ToolStatus.error, message=err.message, error=err)
    return base.model_dump(mode="json")


@mcp.tool()
def resolve_company(ticker: str) -> dict[str, Any]:
    """Resolve a US ticker to CIK and company name (SEC company_tickers)."""
    try:
        inp = ResolveCompanyInput(ticker=ticker)
    except ValidationError as e:
        return _validation_error_payload(e, ResolveCompanyOutput)
    return mcp_tools.to_json_dict(mcp_tools.resolve_company_tool(inp))


@mcp.tool()
def fetch_company_data(ticker: str, refresh: bool = False) -> dict[str, Any]:
    """Download or load cached SEC submissions + companyfacts JSON for one ticker."""
    try:
        inp = FetchCompanyDataInput(ticker=ticker, refresh=refresh)
    except ValidationError as e:
        return _validation_error_payload(e, FetchCompanyDataOutput)
    return mcp_tools.to_json_dict(mcp_tools.fetch_company_data_tool(inp))


@mcp.tool()
def build_panel(tickers: list[str], refresh: bool = False) -> dict[str, Any]:
    """Build the wide quarterly panel and write data/processed/panel.csv."""
    try:
        inp = BuildPanelInput(tickers=tickers, refresh=refresh)
    except ValidationError as e:
        return _validation_error_payload(e, BuildPanelOutput)
    return mcp_tools.to_json_dict(mcp_tools.build_panel_tool(inp))


@mcp.tool()
def compute_features(
    tickers: list[str] | None = None,
    panel_csv_path: str | None = None,
) -> dict[str, Any]:
    """Compute feature columns; pass either tickers (rebuilds panel) or panel_csv_path."""
    try:
        inp = ComputeFeaturesInput(tickers=tickers, panel_csv_path=panel_csv_path)
    except ValidationError as e:
        return _validation_error_payload(e, ComputeFeaturesOutput)
    return mcp_tools.to_json_dict(mcp_tools.compute_features_tool(inp))


@mcp.tool()
def detect_anomalies(
    tickers: list[str] | None = None,
    features_csv_path: str | None = None,
) -> dict[str, Any]:
    """Run anomaly detection; pass either tickers (rebuilds through features) or features_csv_path."""
    try:
        inp = DetectAnomaliesInput(tickers=tickers, features_csv_path=features_csv_path)
    except ValidationError as e:
        return _validation_error_payload(e, DetectAnomaliesOutput)
    return mcp_tools.to_json_dict(mcp_tools.detect_anomalies_tool(inp))


@mcp.tool()
def generate_report(
    anomalies_csv_path: str | None = None,
    features_csv_path: str | None = None,
    use_default_artifact_paths: bool = False,
) -> dict[str, Any]:
    """Write data/artifacts/report.md from anomaly + feature CSVs (or default Phase 1 paths)."""
    try:
        inp = GenerateReportInput(
            anomalies_csv_path=anomalies_csv_path,
            features_csv_path=features_csv_path,
            use_default_artifact_paths=use_default_artifact_paths,
        )
    except ValidationError as e:
        return _validation_error_payload(e, GenerateReportOutput)
    return mcp_tools.to_json_dict(mcp_tools.generate_report_tool(inp))


@mcp.tool()
def run_pipeline(
    tickers: list[str] | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Run the full pipeline and write all Phase 1 artifacts (same as main.py)."""
    try:
        inp = RunPipelineInput(tickers=tickers, refresh=refresh)
    except ValidationError as e:
        return _validation_error_payload(e, RunPipelineOutput)
    return mcp_tools.to_json_dict(mcp_tools.run_pipeline_tool(inp))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting EDGAR MCP server (stdio)")
    mcp.run()


if __name__ == "__main__":
    main()
