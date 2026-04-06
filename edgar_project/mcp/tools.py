"""
MCP tool handlers — thin wrappers around Phase 1 pipeline modules.

Implementation status: **stubs only**. Each handler documents the intended ``src.*`` import
and call pattern; business logic is added in a follow-up pass without changing pipeline code.
"""

from __future__ import annotations

from typing import Any

from .schemas import (
    ErrorResponse,
    ExtractMetricsRequest,
    ExtractMetricsResponse,
    FetchCompanyDataRequest,
    FetchCompanyDataResponse,
    ResolveTickerRequest,
    ResolveTickerResponse,
    RunPipelineRequest,
    RunPipelineResponse,
)


def handle_resolve_ticker(req: ResolveTickerRequest) -> ResolveTickerResponse | ErrorResponse:
    """
    Resolve a ticker symbol to a CIK using SEC company_tickers.json.

    TODO:
        - ``from src.data_fetch import resolve_ticker_to_cik``
        - Return ``ResolveTickerResponse(ticker=..., cik=...)``
    """
    raise NotImplementedError("TODO: wire to src.data_fetch.resolve_ticker_to_cik")


def handle_fetch_company_data(req: FetchCompanyDataRequest) -> FetchCompanyDataResponse | ErrorResponse:
    """
    Fetch (or load from cache) submissions + companyfacts JSON for one ticker.

    TODO:
        - ``from src.data_fetch import get_company_data``
        - Map result keys to ``FetchCompanyDataResponse`` including ``cache_paths`` from
          ``config.DATA_RAW`` / per-ticker filenames written by ``get_company_data``
    """
    raise NotImplementedError("TODO: wire to src.data_fetch.get_company_data")


def handle_extract_metrics(req: ExtractMetricsRequest) -> ExtractMetricsResponse | ErrorResponse:
    """
    Produce long-format metrics for one company.

    TODO:
        - ``get_company_data`` then ``from src.metric_extraction import extract_metrics``
        - ``years`` default: ``import config`` → ``config.YEARS_LOOKBACK``
        - Use ``adapters.dataframe_to_preview`` on the resulting DataFrame
    """
    raise NotImplementedError("TODO: wire to get_company_data + src.metric_extraction.extract_metrics")


def handle_run_pipeline(req: RunPipelineRequest) -> RunPipelineResponse | ErrorResponse:
    """
    Run the full deterministic pipeline and write Phase 1 artifacts.

    TODO:
        - Mirror ``main.py`` sequence: ``get_company_data`` → ``extract_metrics`` →
          ``build_panel`` → ``compute_features`` → ``detect_anomalies`` → ``generate_report``
        - Write the same paths as ``main.py`` (``config.DATA_PROCESSED``, ``config.DATA_ARTIFACTS``)
        - Fill ``ArtifactPaths``, ``RowCounts``, optional ``report_preview``
        - If ``req.tickers`` empty, use ``config.DEFAULT_TICKERS[:5]``
    """
    raise NotImplementedError("TODO: mirror main.py orchestration; no changes to pipeline modules")


# --- Registration metadata (for server.py / MCP SDK) ----------------------

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "name": "edgar_resolve_ticker",
        "description": "Resolve US ticker to SEC CIK.",
        "input_model": ResolveTickerRequest,
        "handler": handle_resolve_ticker,
    },
    {
        "name": "edgar_fetch_company_data",
        "description": "Fetch and cache SEC submissions + companyfacts JSON.",
        "input_model": FetchCompanyDataRequest,
        "handler": handle_fetch_company_data,
    },
    {
        "name": "edgar_extract_metrics",
        "description": "Extract long-format quarterly metrics from company facts.",
        "input_model": ExtractMetricsRequest,
        "handler": handle_extract_metrics,
    },
    {
        "name": "edgar_run_pipeline",
        "description": "Run full EDGAR anomaly pipeline and write standard artifacts.",
        "input_model": RunPipelineRequest,
        "handler": handle_run_pipeline,
    },
]


def register_all_tools(app: Any) -> None:
    """
    Register ``TOOL_DEFINITIONS`` with the MCP server instance.

    Parameters
    ----------
    app:
        TODO: replace ``Any`` with the concrete MCP server type (e.g. FastMCP) once the
        SDK is pinned. Implementation will loop ``TOOL_DEFINITIONS`` and call
        ``@app.tool`` or the SDK's register API.

    Raises
    ------
    NotImplementedError
        Until Phase 2 wiring is complete.
    """
    raise NotImplementedError(
        "TODO: import MCP SDK, bind each TOOL_DEFINITIONS[*].handler with input_model schema"
    )
