"""
Local tabular adapter — CSV and Parquet fixture files.

Fully domain-agnostic: it applies no business hints, so column roles and semantic
types come purely from the general :class:`SchemaProfiler`. Optional generic
hints (a time field, entity-id fields) may be supplied per request; these are
structural, not domain vocabulary.
"""

from __future__ import annotations

from pathlib import Path

from agentic.domain.enums import DatasetKind, Modality

from .base import AdapterInfo, AdapterRequest, InputAdapter
from .capabilities import PermittedOperation, SourceCapabilityDescriptor, SourceType
from .errors import UnsupportedSourceError
from .materialize import DatasetMaterializer, TabularFileMaterializer

ADAPTER_ID = "local_tabular"
ADAPTER_VERSION = "1"

_SUFFIX_SOURCE_TYPE = {
    ".csv": SourceType.csv,
    ".txt": SourceType.csv,
    ".parquet": SourceType.parquet,
    ".pq": SourceType.parquet,
}


class LocalTabularAdapter(InputAdapter):
    """Reads CSV/Parquet files into profiled dataset manifests."""

    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def capabilities(self) -> SourceCapabilityDescriptor:
        return SourceCapabilityDescriptor(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            supported_source_types=[SourceType.csv, SourceType.parquet],
            supported_modalities=[Modality.tabular, Modality.time_series],
            permitted_operations=[
                PermittedOperation.materialize,
                PermittedOperation.profile_schema,
                PermittedOperation.profile_quality,
                PermittedOperation.fingerprint,
                PermittedOperation.full_scan,
            ],
            supports_temporal=True,
            supports_entity_ids=True,
            notes="Generic tabular fixtures; no domain assumptions.",
        )

    def describe(self) -> AdapterInfo:
        return AdapterInfo(
            adapter_id=ADAPTER_ID,
            version=ADAPTER_VERSION,
            title="Local tabular files (CSV/Parquet)",
            description="Profiles local CSV or Parquet fixture files into dataset manifests.",
            default_dataset_kind=DatasetKind.tabular_panel.value,
        )

    def materializer(self, request: AdapterRequest) -> DatasetMaterializer:
        raw_path = request.parameters.get("path")
        if not raw_path:
            raise UnsupportedSourceError("local_tabular requires parameters['path']")
        path = Path(raw_path)
        source_type = _SUFFIX_SOURCE_TYPE.get(path.suffix.lower())
        if source_type is None:
            raise UnsupportedSourceError(
                f"unsupported tabular extension: {path.suffix!r}",
                detail=f"supported: {sorted(_SUFFIX_SOURCE_TYPE)}",
            )
        time_field = request.parameters.get("time_field") or None
        entity_fields = request.parameters.get("entity_id_fields")
        entity_id_fields = [f.strip() for f in entity_fields.split(",") if f.strip()] if entity_fields else []
        return TabularFileMaterializer(
            path,
            adapter_id=ADAPTER_ID,
            source_type=source_type.value,
            entity_id_fields=entity_id_fields,
            time_field=time_field,
        )
