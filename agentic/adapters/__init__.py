"""
Input adapters — the seam that makes the platform input-agnostic.

Each adapter turns a scope request into a
:class:`~agentic.domain.manifest.DatasetManifest` via a shared pipeline:

    InputAdapter.materializer(request) -> DatasetMaterializer
        -> MaterializedDataset
        -> DatasetManifestBuilder( SchemaProfiler, DataQualityProfiler )
        -> DatasetManifest (schema, semantic types, dimensions, temporal bounds,
                            missingness, duplicates, quality warnings, fingerprint,
                            provenance, adapter version)

The general profilers are domain-agnostic; adapters inject any domain knowledge
as hints. The first-party EDGAR adapter keeps the existing deterministic pipeline
working as a demo, reference template, and regression fixture.

See ``docs/adapters/adapter-contract.md`` for the full contract.
"""

from __future__ import annotations

from .base import AdapterInfo, AdapterRequest, InputAdapter
from .capabilities import PermittedOperation, SourceCapabilityDescriptor, SourceType
from .edgar import EDGARAdapter, EdgarInputAdapter
from .errors import (
    AdapterError,
    EmptyDatasetError,
    MalformedDatasetError,
    SourceNotFoundError,
    UnsupportedSourceError,
)
from .manifest_builder import DatasetManifestBuilder
from .materialize import (
    DatasetMaterializer,
    DocumentRecord,
    InMemoryMaterializer,
    MaterializedDataset,
    SchemaOnlyMaterializer,
    TabularFileMaterializer,
)
from .memory import InMemoryDatasetAdapter
from .profiling import DataQualityProfiler, SchemaProfiler, compute_fingerprint
from .registry import AdapterRegistry, build_default_registry, default_registry
from .tabular import LocalTabularAdapter

__all__ = [
    # base seam
    "AdapterInfo",
    "AdapterRequest",
    "InputAdapter",
    # capabilities
    "SourceCapabilityDescriptor",
    "SourceType",
    "PermittedOperation",
    # abstractions
    "DatasetMaterializer",
    "MaterializedDataset",
    "DocumentRecord",
    "TabularFileMaterializer",
    "InMemoryMaterializer",
    "SchemaOnlyMaterializer",
    "SchemaProfiler",
    "DataQualityProfiler",
    "DatasetManifestBuilder",
    "compute_fingerprint",
    # adapters
    "EDGARAdapter",
    "EdgarInputAdapter",
    "LocalTabularAdapter",
    "InMemoryDatasetAdapter",
    # registry
    "AdapterRegistry",
    "build_default_registry",
    "default_registry",
    # errors
    "AdapterError",
    "SourceNotFoundError",
    "UnsupportedSourceError",
    "MalformedDatasetError",
    "EmptyDatasetError",
]
