"""
Pydantic input/output models and a consistent MCP tool response envelope.

Status values:
  * ``success`` — operation completed; tool-specific fields are populated.
  * ``no_data`` — valid request but nothing to return (e.g. empty panel).
  * ``error`` — failure; :class:`ErrorInfo` is populated.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ToolStatus(str, Enum):
    """Unified tool outcome discriminator."""

    success = "success"
    no_data = "no_data"
    error = "error"


class ErrorInfo(BaseModel):
    """Non-silent failure details for clients and logs."""

    code: str = Field(description="Stable machine-readable code, e.g. UNKNOWN_TICKER")
    message: str
    detail: str | None = None


# --- Phase 1 artifact filenames (relative to repo / config paths) ------------

PHASE1_PANEL_CSV = "panel.csv"
PHASE1_FEATURES_CSV = "features.csv"
PHASE1_ANOMALIES_CSV = "anomalies.csv"
PHASE1_REPORT_MD = "report.md"


class ArtifactPaths(BaseModel):
    """Canonical Phase 1 outputs (absolute or normalized paths as strings)."""

    panel_csv: str
    features_csv: str
    anomalies_csv: str
    report_md: str


# --- resolve_company ----------------------------------------------------------

class ResolveCompanyInput(BaseModel):
    ticker: str = Field(min_length=1, description="US equity symbol, e.g. AAPL")


class ResolveCompanyOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    ticker: str | None = None
    cik: int | None = None
    company_name: str | None = None


# --- fetch_company_data -------------------------------------------------------

class FetchCompanyDataInput(BaseModel):
    ticker: str = Field(min_length=1)
    refresh: bool = Field(default=False, description="Bypass cache and refetch SEC JSON")


class FetchCompanyDataOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    ticker: str | None = None
    cik: int | None = None
    cache_paths: dict[str, str] | None = Field(
        default=None,
        description="e.g. submissions, companyfacts → absolute paths",
    )


# --- build_panel --------------------------------------------------------------

class BuildPanelInput(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=5)
    refresh: bool = False


class BuildPanelOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    panel_csv_path: str | None = None
    row_count: int | None = None
    columns: list[str] | None = None


# --- compute_features ---------------------------------------------------------

class ComputeFeaturesInput(BaseModel):
    tickers: list[str] | None = Field(default=None, description="Build panel from these symbols")
    panel_csv_path: str | None = Field(default=None, description="Read existing panel CSV")

    @model_validator(mode="after")
    def exactly_one_source(self) -> ComputeFeaturesInput:
        has_t = self.tickers is not None and len(self.tickers) > 0
        has_p = bool(self.panel_csv_path and self.panel_csv_path.strip())
        if has_t == has_p:
            raise ValueError("Provide exactly one of: non-empty tickers, or panel_csv_path")
        if self.tickers is not None and len(self.tickers) > 5:
            raise ValueError("At most 5 tickers")
        return self


class ComputeFeaturesOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    features_csv_path: str | None = None
    row_count: int | None = None
    columns: list[str] | None = None


# --- detect_anomalies ---------------------------------------------------------

class DetectAnomaliesInput(BaseModel):
    tickers: list[str] | None = Field(default=None)
    features_csv_path: str | None = Field(default=None)

    @model_validator(mode="after")
    def exactly_one_source(self) -> DetectAnomaliesInput:
        has_t = self.tickers is not None and len(self.tickers) > 0
        has_f = bool(self.features_csv_path and self.features_csv_path.strip())
        if has_t == has_f:
            raise ValueError("Provide exactly one of: non-empty tickers, or features_csv_path")
        if self.tickers is not None and len(self.tickers) > 5:
            raise ValueError("At most 5 tickers")
        return self


class DetectAnomaliesOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    anomalies_csv_path: str | None = None
    anomaly_count: int | None = None


# --- generate_report ----------------------------------------------------------

class GenerateReportInput(BaseModel):
    anomalies_csv_path: str | None = None
    features_csv_path: str | None = None
    use_default_artifact_paths: bool = Field(
        default=False,
        description="If True, read anomalies/features from Phase 1 paths under config.DATA_*",
    )

    @model_validator(mode="after")
    def paths_or_default(self) -> GenerateReportInput:
        if self.use_default_artifact_paths:
            return self
        has_a = bool(self.anomalies_csv_path and str(self.anomalies_csv_path).strip())
        has_f = bool(self.features_csv_path and str(self.features_csv_path).strip())
        if not (has_a and has_f):
            raise ValueError(
                "Provide both anomalies_csv_path and features_csv_path, or set use_default_artifact_paths=True"
            )
        return self


class GenerateReportOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    report_md_path: str | None = None


# --- run_pipeline -------------------------------------------------------------

class RunPipelineInput(BaseModel):
    tickers: list[str] | None = Field(
        default=None,
        description="1–5 symbols; omit or empty uses config.DEFAULT_TICKERS",
    )
    refresh: bool = False

    @model_validator(mode="after")
    def tickers_bounds(self) -> RunPipelineInput:
        if self.tickers is None:
            self.tickers = []
        if len(self.tickers) > 5:
            raise ValueError("At most 5 tickers")
        return self


class PipelineSummaryCounts(BaseModel):
    panel_rows: int = 0
    feature_rows: int = 0
    anomaly_rows: int = 0


class RunPipelineOutput(BaseModel):
    status: ToolStatus
    message: str | None = None
    error: ErrorInfo | None = None
    artifacts: ArtifactPaths | None = None
    counts: PipelineSummaryCounts | None = None


# --- Legacy / adapter previews (optional use) --------------------------------

class TabularPreview(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool = False


class ArtifactSummary(BaseModel):
    path: str
    exists: bool = False
    size_bytes: int | None = None
