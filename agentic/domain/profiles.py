"""
Dataset profile value objects — the typed pieces a manifest carries.

These are pure, serializable descriptors (dimensions, temporal bounds,
missingness, duplicates, quality warnings, source identity). The *logic* that
computes them lives in the adapters layer (``agentic.adapters.profiling``); the
*types* live here so the domain manifest stays framework-independent.
"""

from __future__ import annotations

from pydantic import Field

from .common import DomainModel
from .enums import QualitySeverity


class SourceIdentity(DomainModel):
    """Where a materialized dataset came from (adapter + source system)."""

    adapter_id: str = Field(..., min_length=1)
    source_type: str = Field(..., description="Source type token, e.g. 'csv', 'parquet', 'edgar', 'in_memory'.")
    source_name: str = Field(..., min_length=1, description="Human-readable source label.")
    locator: str | None = Field(default=None, description="Opaque handle (path/query/uri); never raw secrets.")


class DatasetDimensions(DomainModel):
    """Coarse size of a dataset."""

    row_count: int = Field(default=0, ge=0, description="Rows (tabular) or documents (document set).")
    column_count: int = Field(default=0, ge=0)
    entity_count: int | None = Field(default=None, ge=0, description="Distinct entity ids, when identifiable.")
    period_count: int | None = Field(default=None, ge=0, description="Distinct time periods, when temporal.")


class TemporalCoverage(DomainModel):
    """Temporal bounds of a dataset (string-encoded to stay dtype-agnostic)."""

    field: str = Field(..., description="Column the coverage is measured on.")
    minimum: str | None = Field(default=None)
    maximum: str | None = Field(default=None)
    distinct_periods: int | None = Field(default=None, ge=0)


class ColumnMissingness(DomainModel):
    """Missing-value summary for one column."""

    column: str
    missing_count: int = Field(ge=0)
    missing_ratio: float = Field(ge=0.0, le=1.0)


class MissingnessSummary(DomainModel):
    """Dataset-wide missingness."""

    total_cells: int = Field(default=0, ge=0)
    missing_cells: int = Field(default=0, ge=0)
    overall_missing_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    by_column: list[ColumnMissingness] = Field(default_factory=list)


class DuplicateSummary(DomainModel):
    """Duplicate-row (and optional key) summary."""

    duplicate_row_count: int = Field(default=0, ge=0)
    duplicate_row_ratio: float = Field(default=0.0, ge=0.0, le=1.0)
    key_fields: list[str] = Field(default_factory=list, description="Fields used for key-duplicate detection, if any.")
    duplicate_key_count: int | None = Field(default=None, ge=0)


class QualityWarning(DomainModel):
    """One structured data-quality finding (never free-form prose alone)."""

    code: str = Field(..., min_length=1, description="Stable code, e.g. COLUMN_ALL_NULL, DUPLICATE_ROWS.")
    severity: QualitySeverity = Field(default=QualitySeverity.warning)
    message: str = Field(..., min_length=1)
    column: str | None = Field(default=None)
