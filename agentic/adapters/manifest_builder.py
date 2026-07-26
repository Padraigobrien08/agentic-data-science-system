"""
DatasetManifestBuilder — assembles a :class:`DatasetManifest` from a materialized
dataset plus the schema and quality profilers.

This is the single place every adapter goes through, so every materialized
dataset yields a manifest with the same required contents: source identity,
content fingerprint, schema, semantic types, dimensions, temporal bounds,
missingness, duplicates, quality warnings, provenance, and adapter version.
"""

from __future__ import annotations

from agentic.domain.manifest import DatasetManifest, DatasetProvenance
from agentic.domain.profiles import SourceIdentity

from .materialize import MaterializedDataset
from .profiling import DataQualityProfiler, SchemaProfiler, compute_fingerprint


class DatasetManifestBuilder:
    """Composes profilers over a materialized dataset into a manifest."""

    def __init__(
        self,
        schema_profiler: SchemaProfiler | None = None,
        quality_profiler: DataQualityProfiler | None = None,
    ) -> None:
        self._schema = schema_profiler or SchemaProfiler()
        self._quality = quality_profiler or DataQualityProfiler()

    def build(
        self,
        materialized: MaterializedDataset,
        *,
        adapter_id: str,
        adapter_version: str,
        description: str | None = None,
        extra_provenance: dict[str, str] | None = None,
    ) -> DatasetManifest:
        columns = self._schema.profile(materialized)
        quality = self._quality.profile(materialized, columns)
        fingerprint = compute_fingerprint(materialized)

        identity: SourceIdentity = materialized.source_identity
        provenance = DatasetProvenance(
            adapter_id=adapter_id,
            adapter_version=adapter_version,
            source=identity.source_name,
            parameters={**materialized.provenance_parameters, **(extra_provenance or {})},
        )

        entities = materialized.entities
        if entities is None:
            entities = self._derive_entities(materialized, columns)

        row_count = None if materialized.is_schema_only() else quality.dimensions.row_count

        return DatasetManifest(
            name=materialized.name,
            description=description,
            adapter_version=adapter_version,
            dataset_kind=materialized.dataset_kind,
            modality=materialized.modality,
            source_identity=identity,
            fingerprint=fingerprint,
            columns=columns,
            entities=entities,
            row_count=row_count,
            dimensions=quality.dimensions,
            temporal_coverage=quality.temporal_coverage,
            missingness=quality.missingness,
            duplicates=quality.duplicates,
            quality_warnings=quality.warnings,
            provenance=provenance,
        )

    @staticmethod
    def _derive_entities(materialized: MaterializedDataset, columns) -> list[str]:
        """Distinct entity values from the first entity_id column, when present."""
        from agentic.domain.enums import ColumnRole

        if not materialized.is_tabular():
            return []
        frame = materialized.frame
        assert frame is not None
        entity_cols = [c.name for c in columns if c.role == ColumnRole.entity_id]
        if not entity_cols or entity_cols[0] not in frame.columns:
            return []
        col = entity_cols[0]
        return sorted({str(v) for v in frame[col].dropna().unique() if str(v).strip()})
