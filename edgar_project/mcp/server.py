"""
MCP stdio server (FastMCP) exposing EDGAR Phase 1 tools.

Run from repository root::

    python -m edgar_project.mcp.server
    python -m edgar_project.mcp server

Local CLI (JSON on stdout, no MCP client)::

    python -m edgar_project.mcp.cli resolve-company AAPL

See ``edgar_project/mcp/README.md`` for usage.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from edgar_project.mcp import adapters as ad
from edgar_project.mcp import tools as mcp_tools
from edgar_project.mcp.adapters import ensure_sys_path
from edgar_project.mcp.schemas import (
    BuildPanelInput,
    ComputeFeaturesInput,
    DetectAnomaliesInput,
    FetchCompanyDataInput,
    GenerateReportInput,
    ResolveCompanyInput,
    RunPipelineInput,
)

ensure_sys_path()

logger = logging.getLogger(__name__)


def _log_tool_call(name: str, **params: Any) -> None:
    """Structured log line for each MCP tool invocation (stdio clients see stderr)."""
    filtered = {k: v for k, v in params.items() if v is not None}
    logger.info("mcp_tool_call name=%s params=%s", name, filtered)


try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:
    raise ImportError(
        "Install the MCP SDK: pip install 'mcp>=1.0'"
    ) from e

mcp = FastMCP("edgar-anomaly-detector")


def _validation_error_dict(exc: ValidationError) -> dict[str, Any]:
    """Serialize Pydantic tool-arg failures to the same JSON envelope as tools."""
    return ad.envelope_from_validation(exc).model_dump(mode="json")


@mcp.tool()
def resolve_company(ticker: str) -> dict[str, Any]:
    """Resolve a US ticker to CIK and company name (SEC company_tickers)."""
    _log_tool_call("resolve_company", ticker=ticker)
    try:
        inp = ResolveCompanyInput(ticker=ticker)
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.resolve_company_tool(inp))


@mcp.tool()
def fetch_company_data(ticker: str, refresh: bool = False) -> dict[str, Any]:
    """Download or load cached SEC submissions + companyfacts JSON for one ticker."""
    _log_tool_call("fetch_company_data", ticker=ticker, refresh=refresh)
    try:
        inp = FetchCompanyDataInput(ticker=ticker, refresh=refresh)
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.fetch_company_data_tool(inp))


@mcp.tool()
def build_panel(tickers: list[str], refresh: bool = False) -> dict[str, Any]:
    """Build the wide quarterly panel and write data/processed/panel.csv."""
    _log_tool_call("build_panel", tickers=tickers, refresh=refresh)
    try:
        inp = BuildPanelInput(tickers=tickers, refresh=refresh)
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.build_panel_tool(inp))


@mcp.tool()
def compute_features(
    tickers: list[str] | None = None,
    panel_csv_path: str | None = None,
) -> dict[str, Any]:
    """Compute feature columns; pass either tickers (rebuilds panel) or panel_csv_path."""
    _log_tool_call(
        "compute_features",
        tickers=tickers,
        panel_csv_path=panel_csv_path,
    )
    try:
        inp = ComputeFeaturesInput(tickers=tickers, panel_csv_path=panel_csv_path)
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.compute_features_tool(inp))


@mcp.tool()
def detect_anomalies(
    tickers: list[str] | None = None,
    features_csv_path: str | None = None,
) -> dict[str, Any]:
    """Run anomaly detection; pass either tickers (rebuilds through features) or features_csv_path."""
    _log_tool_call(
        "detect_anomalies",
        tickers=tickers,
        features_csv_path=features_csv_path,
    )
    try:
        inp = DetectAnomaliesInput(tickers=tickers, features_csv_path=features_csv_path)
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.detect_anomalies_tool(inp))


@mcp.tool()
def generate_report(
    anomalies_csv_path: str | None = None,
    features_csv_path: str | None = None,
    use_default_artifact_paths: bool = False,
) -> dict[str, Any]:
    """Write data/artifacts/report.md from anomaly + feature CSVs (or default Phase 1 paths)."""
    _log_tool_call(
        "generate_report",
        anomalies_csv_path=anomalies_csv_path,
        features_csv_path=features_csv_path,
        use_default_artifact_paths=use_default_artifact_paths,
    )
    try:
        inp = GenerateReportInput(
            anomalies_csv_path=anomalies_csv_path,
            features_csv_path=features_csv_path,
            use_default_artifact_paths=use_default_artifact_paths,
        )
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.generate_report_tool(inp))


@mcp.tool()
def run_pipeline(
    tickers: list[str] | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Run the full pipeline and write all Phase 1 artifacts (same as main.py)."""
    _log_tool_call("run_pipeline", tickers=tickers, refresh=refresh)
    try:
        inp = RunPipelineInput(tickers=tickers, refresh=refresh)
    except ValidationError as e:
        return _validation_error_dict(e)
    return mcp_tools.to_json_dict(mcp_tools.run_pipeline_tool(inp))


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    logger.info("Starting EDGAR MCP server (stdio); tool calls log at INFO")
    mcp.run()


if __name__ == "__main__":
    main()
