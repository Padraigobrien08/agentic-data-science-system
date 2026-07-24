# Input Adapter Contract

The input-adapter architecture makes the platform input-agnostic: any data
source is described as a `DatasetManifest` that the rest of the system analyzes
without knowing where the data came from. EDGAR is one first-party adapter, not a
special case.

Code: `agentic/adapters/`. Domain types: `agentic/domain/`. Nothing here is wired
into production orchestration yet.

## The pipeline

Every adapter produces a manifest through one shared path, so every materialized
dataset yields the same required contents:

```
InputAdapter.materializer(request) -> DatasetMaterializer
      -> MaterializedDataset            (transient: DataFrame or documents + hints)
      -> DatasetManifestBuilder(
             SchemaProfiler,            (generic column roles + semantic types)
             DataQualityProfiler )      (dimensions, missingness, duplicates, temporal, warnings)
      -> DatasetManifest                (typed, serializable)
```

## Abstractions

| Abstraction | File | Responsibility |
|---|---|---|
| `InputAdapter` | `base.py` | Declares `capabilities()`, `describe()`, `materializer(request)`; base `build_manifest()` runs the shared builder. |
| `SourceCapabilityDescriptor` | `capabilities.py` | Static declaration: supported source types, modalities, permitted operations, temporal/entity support. |
| `DatasetMaterializer` | `materialize.py` | Reads exactly one source into a `MaterializedDataset` (frame/documents) + hints. Concrete: `TabularFileMaterializer`, `InMemoryMaterializer`, `SchemaOnlyMaterializer`. |
| `SchemaProfiler` | `profiling.py` | Infers per-column `ColumnRole` + `SemanticType` from values alone (domain-agnostic). |
| `DataQualityProfiler` | `profiling.py` | Computes dimensions, missingness, duplicate, temporal-coverage, and structured quality warnings. |
| `DatasetManifestBuilder` | `manifest_builder.py` | Composes materializer output + profilers + fingerprint into a `DatasetManifest`. |

Supporting: `AdapterRegistry` (select an adapter by id), `compute_fingerprint`,
the `AdapterError` hierarchy.

## What an adapter declares

Split between the **static capability descriptor** and the **per-dataset manifest**:

| Declaration | Where |
|---|---|
| supported source types | `SourceCapabilityDescriptor.supported_source_types` |
| supported modalities | `SourceCapabilityDescriptor.supported_modalities` |
| permitted operations | `SourceCapabilityDescriptor.permitted_operations` |
| available fields | `DatasetManifest.available_fields()` |
| semantic types | `ColumnSpec.semantic_type` per column |
| row / document counts | `DatasetManifest.dimensions` (`row_count`, `column_count`) |
| temporal coverage | `DatasetManifest.temporal_coverage` (when applicable) |
| entity identifiers | `DatasetManifest.entity_id_fields()` |
| quality warnings | `DatasetManifest.quality_warnings` |
| provenance | `DatasetManifest.provenance` (+ `source_identity`) |
| deterministic fingerprint | `DatasetManifest.fingerprint` |

## DatasetManifest required contents

Every materialized dataset produces a `DatasetManifest` containing:

- **source identity** — `source_identity` (`adapter_id`, `source_type`, `source_name`, `locator`)
- **content fingerprint** — `fingerprint` (`sha256:…`)
- **schema** — `columns: [ColumnSpec]` (name, dtype, role, nullable, unit)
- **semantic types** — `ColumnSpec.semantic_type`
- **dimensions** — `dimensions` (rows/documents, columns, entity/period counts)
- **temporal bounds where applicable** — `temporal_coverage`
- **missingness summary** — `missingness` (per-column + overall)
- **duplicate summary** — `duplicates` (rows + optional key duplicates)
- **quality warnings** — `quality_warnings: [QualityWarning]` (structured code/severity)
- **provenance** — `provenance` (adapter id/version, source, parameters)
- **adapter version** — `adapter_version`

## Determinism

`compute_fingerprint` is a pure content hash. For tabular data it hashes the
canonical CSV serialization plus a column/dtype header; for documents it hashes
the sorted `(id, sha256(text))` pairs; for schema-only manifests it hashes the
declared schema. **Identical inputs produce identical fingerprints** across files,
formats (CSV vs Parquet with the same content), and in-memory frames — proven by
`tests/agentic/test_adapter_architecture.py`.

## Structured failures

Malformed or unavailable inputs raise a typed `AdapterError` with a stable `code`
and `to_dict()`, never a raw framework exception:

| Error | code | When |
|---|---|---|
| `SourceNotFoundError` | `SOURCE_NOT_FOUND` | file/query/records missing (also a `FileNotFoundError`) |
| `UnsupportedSourceError` | `UNSUPPORTED_SOURCE` | adapter can't service the type/extension |
| `MalformedDatasetError` | `MALFORMED_DATASET` | source exists but won't parse |
| `EmptyDatasetError` | `EMPTY_DATASET` | parsed but no rows/documents |

## The domain-agnostic rule

The general layer (`SchemaProfiler`, `DataQualityProfiler`, `DatasetMaterializer`,
`DatasetManifestBuilder`) must contain **no domain vocabulary**. It infers roles
and semantic types from values only. Domain knowledge (which column is an entity,
which is monetary, which is the time axis) enters solely as **hints** on the
`MaterializedDataset`, supplied by the adapter. A static test
(`test_general_processing_modules_contain_no_domain_vocabulary`) guards this, and
a behavioral test proves the general profiler does not promote an EDGAR-shaped
`ticker` column to an entity id or treat `revenue` as monetary without hints.

## Modalities supported

Tabular files, relational query results, API-provided records (via
`InMemoryMaterializer(records=…)`), document collections (`DocumentRecord`),
time-series datasets, and EDGAR financial data — each expressed as a `Modality`
on the manifest.

## Implemented adapters

1. `EDGARAdapter` — [`edgar-adapter.md`](./edgar-adapter.md)
2. `LocalTabularAdapter` (CSV/Parquet) — [`tabular-adapter.md`](./tabular-adapter.md)
3. `InMemoryDatasetAdapter` — for tests and in-process pipelines (frames, records,
   or documents supplied at construction).

## Writing a new adapter

1. Subclass `InputAdapter`; set `adapter_id` and `adapter_version`.
2. Implement `capabilities()` and `describe()`.
3. Implement `materializer(request)` returning a `DatasetMaterializer`. Inject any
   domain knowledge as hints on the materialized dataset — never in the general
   profilers.
4. Rely on the base `build_manifest()` (override only to add provenance, as
   `EDGARAdapter` does).
5. Register in `build_default_registry()` if it should be discoverable by default.
