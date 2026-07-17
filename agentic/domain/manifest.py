"""
Dataset manifests — the input-agnostic description of what a run analyzes.

A manifest is produced by an input adapter (see :mod:`agentic.adapters`) and is
the contract the planner and deterministic tools read instead of assuming an
EDGAR panel. Manifests are pure, typed, and JSON-serializable via
``model_dump(mode="json")``; they carry provenance so a run is reproducible
from persisted state.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, Field

from .enums import ColumnRole, DatasetKind


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ColumnSpec(BaseModel):
    """One column in a dataset, described by semantic role rather than storage."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., min_length=1, description="Column name as it appears in the dataset.")
    dtype: str = Field(default="unknown", description="Storage/interpretation dtype, e.g. float, str, period.")
    role: ColumnRole = Field(..., description="Semantic role used by planner/tool selection.")
    nullable: bool = Field(default=True, description="Whether missing values are expected.")
    unit: str | None = Field(default=None, description="Measurement unit for metric columns (e.g. USD, ratio).")
    description: str | None = Field(default=None, max_length=512)


class DatasetProvenance(BaseModel):
    """Where a manifest's data came from and how to reproduce it."""

    model_config = {"extra": "forbid"}

    adapter_id: str = Field(..., description="Adapter that produced the manifest, e.g. 'edgar'.")
    adapter_version: str = Field(default="1", description="Adapter contract version for reproducibility.")
    source: str = Field(..., description="Human-readable source label, e.g. 'SEC EDGAR companyfacts'.")
    fetched_at: datetime = Field(default_factory=_utc_now)
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe request parameters that generated this manifest (audit/reproduction).",
    )


class DatasetManifest(BaseModel):
    """
    Typed description of a dataset an investigation will analyze.

    Deterministic tools bind to columns by :class:`ColumnRole`, so the same
    planner and experiment machinery works across any adapter that can emit a
    manifest — not only the first-party EDGAR panel.
    """

    model_config = {"extra": "forbid"}

    manifest_id: str = Field(default_factory=lambda: str(uuid4()))
    schema_version: str = Field(default="1")
    name: str = Field(..., min_length=1, description="Short dataset label.")
    description: str | None = Field(default=None, max_length=512)
    dataset_kind: DatasetKind = Field(default=DatasetKind.tabular_panel)
    columns: list[ColumnSpec] = Field(default_factory=list)
    entities: list[str] = Field(
        default_factory=list,
        description="Units of analysis in scope (e.g. tickers).",
    )
    row_count: int | None = Field(default=None, ge=0, description="Row count when materialized offline.")
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Role key -> artifact URI/path (reuses existing artifact-path conventions).",
    )
    provenance: DatasetProvenance

    def columns_with_role(self, role: ColumnRole) -> list[ColumnSpec]:
        """All columns carrying ``role`` (e.g. every metric the tools can analyze)."""
        return [c for c in self.columns if c.role == role]

    def metric_names(self) -> list[str]:
        """Convenience accessor for metric column names in declaration order."""
        return [c.name for c in self.columns_with_role(ColumnRole.metric)]

    def entity_id_column(self) -> ColumnSpec | None:
        """First column carrying the entity_id role, if any."""
        cols = self.columns_with_role(ColumnRole.entity_id)
        return cols[0] if cols else None

    def time_index_column(self) -> ColumnSpec | None:
        """First column carrying the time_index role, if any."""
        cols = self.columns_with_role(ColumnRole.time_index)
        return cols[0] if cols else None
