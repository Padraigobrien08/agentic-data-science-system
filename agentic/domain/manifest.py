"""
Dataset entities — the input-agnostic description of what an investigation analyzes.

Lineage: a :class:`DataSource` (a system) yields a :class:`DatasetReference` (a
concrete dataset instance), whose schema is described by a :class:`DatasetManifest`.
Deterministic tools bind to columns by :class:`~agentic.domain.enums.ColumnRole`,
so the same machinery works for any adapter that can emit a manifest. All types
are pure and JSON-serializable via ``model_dump(mode="json")``.

The module name is kept as ``manifest`` for import stability (input adapters
import :class:`DatasetManifest`, :class:`ColumnSpec`, :class:`DatasetProvenance`
from here).
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel, new_id, utc_now
from .enums import ColumnRole, DatasetKind, DataSourceKind, Modality, SemanticType
from .profiles import (
    DatasetDimensions,
    DuplicateSummary,
    MissingnessSummary,
    QualityWarning,
    SourceIdentity,
    TemporalCoverage,
)


class DataSource(DomainModel):
    """A system data can be acquired from (the EDGAR SEC API is one instance)."""

    id: str = Field(default_factory=lambda: new_id("src"))
    kind: DataSourceKind
    name: str = Field(..., min_length=1)
    description: str | None = Field(default=None, max_length=512)
    adapter_id: str | None = Field(
        default=None,
        description="Input adapter that services this source, e.g. 'edgar'.",
    )
    connection_ref: str | None = Field(
        default=None,
        description="Opaque connection/locator hint (never raw secrets).",
    )
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe source options for reproduction.",
    )
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)


class ColumnSpec(DomainModel):
    """One column, described by semantic role rather than storage dtype."""

    name: str = Field(..., min_length=1)
    dtype: str = Field(default="unknown", description="Storage/interpretation dtype, e.g. float, str, period.")
    role: ColumnRole
    semantic_type: SemanticType = Field(
        default=SemanticType.unknown,
        description="Generic value interpretation, inferred by the schema profiler.",
    )
    nullable: bool = Field(default=True)
    unit: str | None = Field(default=None, description="Measurement unit for metric columns (e.g. USD, ratio).")
    description: str | None = Field(default=None, max_length=512)


class DatasetOrigin(str, Enum):
    """Where a dataset's rows actually came from.

    Carried so a reader is never left to infer it. A showcase that publishes runs over
    generated data beside runs over live filings, and labels neither, is asking the reader to
    take the harder claim on trust — and a system whose whole argument is that it reports what
    it can and cannot support does not get to be vague about its own inputs.
    """

    live = "live"
    """Fetched from a real external source (e.g. SEC EDGAR filings)."""
    synthetic = "synthetic"
    """Generated, usually to exhibit a specific structure. Real numbers, invented world."""
    user_upload = "user_upload"
    """Supplied by whoever asked the question."""
    unknown = "unknown"


class DatasetProvenance(DomainModel):
    """Lineage of a manifest's data (distinct from agent-decision provenance)."""

    adapter_id: str = Field(..., description="Adapter that produced the manifest, e.g. 'edgar'.")
    adapter_version: str = Field(default="1")
    source: str = Field(..., description="Human-readable source label, e.g. 'SEC EDGAR companyfacts'.")
    origin: DatasetOrigin = Field(
        default=DatasetOrigin.unknown,
        description="Live, synthetic, or user-supplied — surfaced to the reader, never inferred.",
    )
    fetched_at: datetime = Field(default_factory=utc_now)
    parameters: dict[str, str] = Field(
        default_factory=dict,
        description="JSON-safe request parameters that generated this manifest.",
    )


class DatasetManifest(DomainModel):
    """Typed description of a dataset an investigation will analyze."""

    manifest_id: str = Field(default_factory=lambda: new_id("mfst"))
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
    adapter_version: str | None = Field(default=None, description="Version of the adapter that built this manifest.")
    name: str = Field(..., min_length=1)
    description: str | None = Field(default=None, max_length=512)
    dataset_kind: DatasetKind = Field(default=DatasetKind.tabular_panel)
    modality: Modality = Field(default=Modality.tabular)
    data_source_id: str | None = Field(default=None)
    dataset_reference_id: str | None = Field(default=None)
    source_identity: SourceIdentity | None = Field(default=None)
    fingerprint: str | None = Field(
        default=None,
        description="Deterministic content fingerprint; identical inputs -> identical value.",
    )
    columns: list[ColumnSpec] = Field(default_factory=list)
    entities: list[str] = Field(default_factory=list, description="Units of analysis in scope (e.g. tickers).")
    row_count: int | None = Field(default=None, ge=0)
    dimensions: DatasetDimensions | None = Field(default=None)
    temporal_coverage: TemporalCoverage | None = Field(default=None)
    missingness: MissingnessSummary | None = Field(default=None)
    duplicates: DuplicateSummary | None = Field(default=None)
    quality_warnings: list[QualityWarning] = Field(default_factory=list)
    artifacts: dict[str, str] = Field(
        default_factory=dict,
        description="Role key -> artifact URI/path.",
    )
    provenance: DatasetProvenance

    def entity_id_fields(self) -> list[str]:
        """Names of columns that identify the unit of analysis."""
        return [c.name for c in self.columns_with_role(ColumnRole.entity_id)]

    def available_fields(self) -> list[str]:
        """All column names present in the dataset."""
        return [c.name for c in self.columns]

    def columns_with_role(self, role: ColumnRole) -> list[ColumnSpec]:
        return [c for c in self.columns if c.role == role]

    def metric_names(self) -> list[str]:
        return [c.name for c in self.columns_with_role(ColumnRole.metric)]

    def entity_id_column(self) -> ColumnSpec | None:
        cols = self.columns_with_role(ColumnRole.entity_id)
        return cols[0] if cols else None

    def time_index_column(self) -> ColumnSpec | None:
        cols = self.columns_with_role(ColumnRole.time_index)
        return cols[0] if cols else None


class DatasetReference(DomainModel):
    """
    A stable pointer to a concrete dataset instance from a :class:`DataSource`.

    ``locator`` is an opaque handle (path, query id, URI); ``content_hash`` makes
    the exact bytes reproducible. An optional embedded :class:`DatasetManifest`
    describes its schema.
    """

    id: str = Field(default_factory=lambda: new_id("dset"))
    data_source_id: str | None = Field(default=None)
    name: str = Field(..., min_length=1)
    locator: str = Field(..., description="Opaque handle to the dataset (path/query/uri).")
    content_hash: str | None = Field(default=None, description="Hash of materialized bytes for reproduction.")
    row_count: int | None = Field(default=None, ge=0)
    retrieved_at: datetime | None = Field(default=None)
    manifest: DatasetManifest | None = Field(default=None)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
