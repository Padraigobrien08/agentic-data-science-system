"""
In-memory dataset adapter — for tests and in-process pipelines.

Holds an already-materialized frame, record list, or document collection. Because
the payload lives in memory (not a serializable request), the data is supplied at
construction; :meth:`build_manifest` profiles it like any other source.
"""

from __future__ import annotations

from typing import Any

from agentic.domain.enums import DatasetKind, Modality

from .base import AdapterInfo, AdapterRequest, InputAdapter
from .capabilities import PermittedOperation, SourceCapabilityDescriptor, SourceType
from .materialize import DatasetMaterializer, DocumentRecord, InMemoryMaterializer

ADAPTER_ID = "in_memory"
ADAPTER_VERSION = "1"


class InMemoryDatasetAdapter(InputAdapter):
    """Wraps an in-memory dataset (frame/records/documents) as an input adapter."""

    adapter_id = ADAPTER_ID
    adapter_version = ADAPTER_VERSION

    def __init__(
        self,
        *,
        name: str = "in_memory_dataset",
        frame: Any | None = None,
        records: list[dict] | None = None,
        documents: list[DocumentRecord] | None = None,
        role_hints: dict | None = None,
        semantic_hints: dict | None = None,
        unit_hints: dict[str, str] | None = None,
        entity_id_fields: list[str] | None = None,
        time_field: str | None = None,
    ) -> None:
        self._name = name
        self._frame = frame
        self._records = records
        self._documents = documents
        self._role_hints = role_hints or {}
        self._semantic_hints = semantic_hints or {}
        self._unit_hints = unit_hints or {}
        self._entity_id_fields = entity_id_fields or []
        self._time_field = time_field
        self._is_documents = documents is not None

    def capabilities(self) -> SourceCapabilityDescriptor:
        return SourceCapabilityDescriptor(
            adapter_id=ADAPTER_ID,
            adapter_version=ADAPTER_VERSION,
            supported_source_types=[SourceType.in_memory],
            supported_modalities=[Modality.tabular, Modality.document, Modality.api_records],
            permitted_operations=[
                PermittedOperation.materialize,
                PermittedOperation.profile_schema,
                PermittedOperation.profile_quality,
                PermittedOperation.fingerprint,
            ],
            supports_temporal=self._time_field is not None,
            supports_entity_ids=bool(self._entity_id_fields),
            notes="In-memory dataset for tests and in-process pipelines.",
        )

    def describe(self) -> AdapterInfo:
        kind = DatasetKind.document_set if self._is_documents else DatasetKind.tabular_panel
        return AdapterInfo(
            adapter_id=ADAPTER_ID,
            version=ADAPTER_VERSION,
            title="In-memory dataset",
            description="Profiles an already-materialized in-memory dataset.",
            default_dataset_kind=kind.value,
        )

    def materializer(self, request: AdapterRequest) -> DatasetMaterializer:
        return InMemoryMaterializer(
            adapter_id=ADAPTER_ID,
            name=self._name,
            frame=self._frame,
            records=self._records,
            documents=self._documents,
            role_hints=self._role_hints,
            semantic_hints=self._semantic_hints,
            unit_hints=self._unit_hints,
            entity_id_fields=self._entity_id_fields,
            time_field=self._time_field,
        )
