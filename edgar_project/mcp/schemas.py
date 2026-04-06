"""
Pydantic request/response models for MCP tool I/O.

These mirror artifact paths and pipeline outputs; wire-up to ``src.*`` happens in ``tools.py``.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# --- Shared / artifacts -------------------------------------------------

class ArtifactPaths(BaseModel):
    """Fixed Phase 1 artifact locations (strings are repo-relative or absolute)."""

    panel_csv: str = Field(description="Path to data/processed/panel.csv")
    features_csv: str = Field(description="Path to data/processed/features.csv")
    anomalies_csv: str = Field(description="Path to data/artifacts/anomalies.csv")
    report_md: str = Field(description="Path to data/artifacts/report.md")


class ArtifactSummary(BaseModel):
    """Lightweight file metadata after read/write."""

    path: str
    exists: bool = False
    size_bytes: int | None = None


# --- resolve_ticker / fetch ------------------------------------------------

class ResolveTickerRequest(BaseModel):
    ticker: str = Field(min_length=1, description="US equity symbol, e.g. AAPL")


class ResolveTickerResponse(BaseModel):
    ticker: str
    cik: int


class FetchCompanyDataRequest(BaseModel):
    ticker: str
    refresh: bool = Field(default=False, description="If True, bypass cache and refetch SEC JSON")


class FetchCompanyDataResponse(BaseModel):
    ticker: str
    cik: int
    cik10: str
    cache_paths: dict[str, str] = Field(
        description="Keys e.g. submissions, companyfacts → local JSON paths"
    )
    refresh_used: bool


# --- pipeline steps (incremental) -----------------------------------------

class ExtractMetricsRequest(BaseModel):
    """TODO: pass ticker or (facts handle); implementation will call get_company_data + extract_metrics."""

    ticker: str
    years: int | None = Field(default=None, description="Defaults to config.YEARS_LOOKBACK")


class TabularPreview(BaseModel):
    """JSON-safe table preview."""

    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool = False


class ExtractMetricsResponse(BaseModel):
    cik: int
    table: TabularPreview


class RunPipelineRequest(BaseModel):
    """TODO: align with config.DEFAULT_TICKERS semantics (max 5 tickers)."""

    tickers: list[str] = Field(default_factory=list, description="Empty → use config defaults")


class RowCounts(BaseModel):
    panel: int = 0
    features: int = 0
    anomalies: int = 0


class RunPipelineResponse(BaseModel):
    tickers: list[str]
    artifacts: ArtifactPaths
    summaries: dict[str, ArtifactSummary] = Field(default_factory=dict)
    row_counts: RowCounts = Field(default_factory=RowCounts)
    report_preview: str | None = Field(
        default=None, description="Optional first N chars of markdown report"
    )


class ErrorResponse(BaseModel):
    """Structured tool error for MCP clients."""

    error: str
    detail: str | None = None
