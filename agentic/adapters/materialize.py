"""
Materialization — turning a source into in-memory data to profile.

A :class:`DatasetMaterializer` reads exactly one source and returns a transient
:class:`MaterializedDataset` (a DataFrame for tabular/time-series, or documents
for document collections) plus source identity and optional *hints*. Hints are
how an adapter injects domain knowledge (column roles/units for a specific
source) **without** the general schema/quality profilers knowing any domain
vocabulary.

``MaterializedDataset`` is a plain dataclass (not a domain model): it holds live
pandas objects and is never serialized.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from agentic.domain.enums import ColumnRole, DatasetKind, Modality, SemanticType
from agentic.domain.manifest import ColumnSpec
from agentic.domain.profiles import SourceIdentity

from .errors import EmptyDatasetError, MalformedDatasetError, SourceNotFoundError


@dataclass(frozen=True)
class DocumentRecord:
    """One document in a document-collection dataset."""

    id: str
    text: str
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass
class MaterializedDataset:
    """Transient in-memory dataset plus adapter-supplied descriptive hints."""

    source_identity: SourceIdentity
    modality: Modality = Modality.tabular
    dataset_kind: DatasetKind = DatasetKind.tabular_panel
    name: str = "dataset"
    provenance_parameters: dict[str, str] = field(default_factory=dict)

    # Exactly one payload form is populated (or declared_columns for schema-only).
    frame: pd.DataFrame | None = None
    documents: list[DocumentRecord] | None = None
    declared_columns: list[ColumnSpec] | None = None

    # Optional domain hints (adapter-supplied; the general layer never guesses these).
    role_hints: dict[str, ColumnRole] = field(default_factory=dict)
    semantic_hints: dict[str, SemanticType] = field(default_factory=dict)
    unit_hints: dict[str, str] = field(default_factory=dict)
    entity_id_fields: list[str] = field(default_factory=list)
    time_field: str | None = None
    entities: list[str] | None = None

    def is_schema_only(self) -> bool:
        return self.frame is None and self.documents is None and self.declared_columns is not None

    def is_tabular(self) -> bool:
        return self.frame is not None

    def is_documents(self) -> bool:
        return self.documents is not None


class DatasetMaterializer(ABC):
    """Reads one source into a :class:`MaterializedDataset`."""

    @abstractmethod
    def materialize(self) -> MaterializedDataset:
        raise NotImplementedError


class TabularFileMaterializer(DatasetMaterializer):
    """Materialize a CSV or Parquet file into a DataFrame (domain-agnostic)."""

    def __init__(
        self,
        path: str | Path,
        *,
        adapter_id: str,
        source_type: str,
        name: str | None = None,
        modality: Modality = Modality.tabular,
        dataset_kind: DatasetKind = DatasetKind.tabular_panel,
        role_hints: dict[str, ColumnRole] | None = None,
        semantic_hints: dict[str, SemanticType] | None = None,
        unit_hints: dict[str, str] | None = None,
        entity_id_fields: list[str] | None = None,
        time_field: str | None = None,
    ) -> None:
        self._path = Path(path)
        self._adapter_id = adapter_id
        self._source_type = source_type
        self._name = name or self._path.name
        self._modality = modality
        self._dataset_kind = dataset_kind
        self._role_hints = role_hints or {}
        self._semantic_hints = semantic_hints or {}
        self._unit_hints = unit_hints or {}
        self._entity_id_fields = entity_id_fields or []
        self._time_field = time_field

    def _read(self) -> pd.DataFrame:
        p = self._path
        if not p.is_file():
            raise SourceNotFoundError(f"tabular source not found: {p}", detail=str(p))
        suffix = p.suffix.lower()
        try:
            if suffix in (".parquet", ".pq"):
                return pd.read_parquet(p)
            if suffix in (".csv", ".txt"):
                return pd.read_csv(p)
            # Fall back to extension-inferred; still structured on failure.
            return pd.read_csv(p)
        except SourceNotFoundError:
            raise
        except Exception as exc:  # noqa: BLE001 - boundary: normalize to structured failure
            raise MalformedDatasetError(
                f"could not parse tabular source: {p}",
                detail=f"{type(exc).__name__}: {exc}",
            ) from exc

    def materialize(self) -> MaterializedDataset:
        frame = self._read()
        if frame.shape[1] == 0:
            raise MalformedDatasetError(f"source has no columns: {self._path}", detail=str(self._path))
        if len(frame) == 0:
            raise EmptyDatasetError(f"source has no rows: {self._path}", detail=str(self._path))
        return MaterializedDataset(
            source_identity=SourceIdentity(
                adapter_id=self._adapter_id,
                source_type=self._source_type,
                source_name=self._name,
                locator=str(self._path),
            ),
            modality=self._modality,
            dataset_kind=self._dataset_kind,
            name=self._name,
            provenance_parameters={"path": str(self._path), "format": self._source_type},
            frame=frame,
            role_hints=self._role_hints,
            semantic_hints=self._semantic_hints,
            unit_hints=self._unit_hints,
            entity_id_fields=self._entity_id_fields,
            time_field=self._time_field,
        )


class InMemoryMaterializer(DatasetMaterializer):
    """Materialize an already-in-memory frame or document list (tests/pipelines)."""

    def __init__(
        self,
        *,
        adapter_id: str = "in_memory",
        name: str = "in_memory_dataset",
        frame: pd.DataFrame | None = None,
        records: list[dict] | None = None,
        documents: list[DocumentRecord] | None = None,
        modality: Modality = Modality.tabular,
        dataset_kind: DatasetKind = DatasetKind.tabular_panel,
        role_hints: dict[str, ColumnRole] | None = None,
        semantic_hints: dict[str, SemanticType] | None = None,
        unit_hints: dict[str, str] | None = None,
        entity_id_fields: list[str] | None = None,
        time_field: str | None = None,
    ) -> None:
        provided = [x for x in (frame is not None, records is not None, documents is not None) if x]
        if len(provided) != 1:
            raise MalformedDatasetError(
                "InMemoryMaterializer requires exactly one of frame/records/documents"
            )
        self._adapter_id = adapter_id
        self._name = name
        self._frame = frame
        self._records = records
        self._documents = documents
        self._modality = modality if documents is None else Modality.document
        self._dataset_kind = dataset_kind if documents is None else DatasetKind.document_set
        self._role_hints = role_hints or {}
        self._semantic_hints = semantic_hints or {}
        self._unit_hints = unit_hints or {}
        self._entity_id_fields = entity_id_fields or []
        self._time_field = time_field

    def materialize(self) -> MaterializedDataset:
        identity = SourceIdentity(
            adapter_id=self._adapter_id,
            source_type="in_memory",
            source_name=self._name,
        )
        if self._documents is not None:
            if not self._documents:
                raise EmptyDatasetError("no documents provided")
            return MaterializedDataset(
                source_identity=identity,
                modality=Modality.document,
                dataset_kind=DatasetKind.document_set,
                name=self._name,
                documents=list(self._documents),
            )
        if self._records is not None:
            if not self._records:
                raise EmptyDatasetError("no records provided")
            frame = pd.DataFrame.from_records(self._records)
        else:
            frame = self._frame
        assert frame is not None
        if frame.shape[1] == 0:
            raise MalformedDatasetError("in-memory frame has no columns")
        if len(frame) == 0:
            raise EmptyDatasetError("in-memory frame has no rows")
        return MaterializedDataset(
            source_identity=identity,
            modality=self._modality,
            dataset_kind=self._dataset_kind,
            name=self._name,
            frame=frame.reset_index(drop=True),
            role_hints=self._role_hints,
            semantic_hints=self._semantic_hints,
            unit_hints=self._unit_hints,
            entity_id_fields=self._entity_id_fields,
            time_field=self._time_field,
        )


class SchemaOnlyMaterializer(DatasetMaterializer):
    """Declare a dataset's schema without materializing data (offline manifests)."""

    def __init__(
        self,
        *,
        adapter_id: str,
        source_type: str,
        name: str,
        columns: list[ColumnSpec],
        entities: list[str] | None = None,
        modality: Modality = Modality.tabular,
        dataset_kind: DatasetKind = DatasetKind.tabular_panel,
        provenance_parameters: dict[str, str] | None = None,
    ) -> None:
        self._identity = SourceIdentity(
            adapter_id=adapter_id, source_type=source_type, source_name=name
        )
        self._name = name
        self._columns = columns
        self._entities = entities
        self._modality = modality
        self._dataset_kind = dataset_kind
        self._params = provenance_parameters or {}

    def materialize(self) -> MaterializedDataset:
        return MaterializedDataset(
            source_identity=self._identity,
            modality=self._modality,
            dataset_kind=self._dataset_kind,
            name=self._name,
            provenance_parameters=self._params,
            declared_columns=list(self._columns),
            entities=list(self._entities) if self._entities is not None else None,
        )
