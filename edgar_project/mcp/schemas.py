"""
MCP tool inputs and the unified response contract.

Every tool returns :class:`ToolResponseEnvelope` (serialized with ``model_dump(mode="json")``).

Shape::

    {
      "status": "success" | "no_data" | "error",
      "message": str,
      "data": { ... },       # tool-specific; empty {} when nothing to add
      "artifacts": { ... },  # paths or artifact hints; empty {} when none
      "errors": [ ... ]      # empty on success/no_data; one+ items on error
    }
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, model_validator


class ToolStatus(str, Enum):
    success = "success"
    no_data = "no_data"
    error = "error"


class ErrorInfo(BaseModel):
    """Single error entry (machine-friendly; optional debug fields)."""

    code: str = Field(description="Stable code, e.g. UNKNOWN_TICKER, SEC_FETCH_ERROR")
    message: str
    detail: str | None = Field(default=None, description="Longer text, stack context, or JSON")
    http_status: int | None = Field(
        default=None,
        description="Set when the failure is an HTTP response (e.g. SEC 403)",
    )
    exc_type: str | None = Field(
        default=None,
        description="Python exception type name for unexpected errors",
    )


class ToolResponseEnvelope(BaseModel):
    """
    Stable contract for all MCP tool responses.

    Rules:
      * ``errors`` — empty list for ``success`` and ``no_data``; non-empty for ``error``.
      * ``data`` — tool-specific payload; use ``{}`` if nothing to return.
      * ``artifacts`` — paths (strings) keyed by role, e.g. ``panel_csv``; use ``{}`` if none.

    ``data`` often includes provenance helpers (when applicable): ``input_tickers``,
    ``resolved_ciks`` (``{ticker, cik}`` rows), ``ciks`` (distinct ints),
    ``primary_artifact`` / ``artifacts_detail`` (path, ``updated_at``, row/column shape),
    and for anomalies ``zscore_window``, ``zscore_threshold``, ``metrics_analyzed``.
    """

    status: ToolStatus
    message: str = ""
    data: dict[str, Any] = Field(default_factory=dict)
    artifacts: dict[str, Any] = Field(default_factory=dict)
    errors: list[ErrorInfo] = Field(default_factory=list)

    @model_validator(mode="after")
    def _errors_match_status(self) -> ToolResponseEnvelope:
        if self.status == ToolStatus.error:
            if not self.errors:
                raise ValueError("status=error requires at least one entry in errors")
        elif self.errors:
            raise ValueError("status success/no_data must have errors=[]")
        return self


# --- Inputs (unchanged semantics) --------------------------------------------

class ResolveCompanyInput(BaseModel):
    ticker: str = Field(min_length=1, description="US equity symbol, e.g. AAPL")


class FetchCompanyDataInput(BaseModel):
    ticker: str = Field(min_length=1)
    refresh: bool = Field(default=False, description="Bypass cache and refetch SEC JSON")


class BuildPanelInput(BaseModel):
    tickers: list[str] = Field(min_length=1, max_length=5)
    refresh: bool = False


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


# --- Legacy helpers (adapters / previews) ------------------------------------

class TabularPreview(BaseModel):
    columns: list[str]
    rows: list[dict[str, Any]]
    row_count: int
    truncated: bool = False


class ArtifactSummary(BaseModel):
    path: str
    exists: bool = False
    size_bytes: int | None = None


# Phase 1 artifact key names (for ``artifacts`` dict)
ARTIFACT_KEY_PANEL = "panel_csv"
ARTIFACT_KEY_FEATURES = "features_csv"
ARTIFACT_KEY_ANOMALIES = "anomalies_csv"
ARTIFACT_KEY_REPORT = "report_md"
ARTIFACT_KEY_DATA_QUALITY = "data_quality_csv"
ARTIFACT_KEY_EXCLUSIONS = "exclusions_csv"
ARTIFACT_KEY_CACHE_SUBMISSIONS = "cache_submissions_json"
ARTIFACT_KEY_CACHE_COMPANYFACTS = "cache_companyfacts_json"

# Stable error codes (use in ``errors[].code``)
CODE_UNKNOWN_TICKER = "UNKNOWN_TICKER"
CODE_SEC_FETCH = "SEC_FETCH_ERROR"
CODE_VALIDATION = "VALIDATION_ERROR"
CODE_EMPTY_INPUT = "EMPTY_INPUT"
CODE_FILE_NOT_FOUND = "FILE_NOT_FOUND"
CODE_INTERNAL = "INTERNAL_ERROR"
