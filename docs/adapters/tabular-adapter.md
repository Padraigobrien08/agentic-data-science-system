# Local Tabular Adapter

`LocalTabularAdapter` (`agentic/adapters/tabular.py`, `adapter_id =
"local_tabular"`) profiles local **CSV and Parquet** fixture files into dataset
manifests. It is the reference **domain-agnostic** adapter: it injects no
business hints, so column roles and semantic types come purely from the general
`SchemaProfiler`.

## Capabilities

| Field | Value |
|---|---|
| source types | `csv`, `parquet` |
| modalities | `tabular`, `time_series` |
| permitted ops | materialize, profile_schema, profile_quality, fingerprint, full_scan |
| temporal | yes (when a time field is identified/supplied) |
| entity ids | yes (when supplied) |
| adapter version | `1` |

## Request

`build_manifest(AdapterRequest(parameters=…))`:

| Parameter | Required | Meaning |
|---|---|---|
| `path` | yes | Path to a `.csv`/`.txt` or `.parquet`/`.pq` file. |
| `time_field` | no | Column to treat as the time axis (structural hint, not domain vocabulary). |
| `entity_id_fields` | no | Comma-separated columns identifying the unit of analysis. |

`time_field` / `entity_id_fields` are *structural* hints a user supplies about
their own file; they are not baked-in domain knowledge. Without them, roles and
semantic types are inferred entirely from values.

## Generic inference

`SchemaProfiler` assigns each column a `SemanticType` from its values and a
generic `ColumnRole`:

| Values look like | SemanticType | Role |
|---|---|---|
| boolean dtype | `boolean` | dimension |
| integer dtype | `integer` | metric |
| float dtype | `real` | metric |
| datetime dtype | `temporal` | time_index |
| all-unique strings (n>1) | `identifier` | identifier |
| low-cardinality strings | `categorical` | dimension |
| high-cardinality strings | `text` | dimension |

Units (`monetary`, `percentage`) are never inferred — they require domain
knowledge and are supplied only by domain adapters as hints.

## Quality profiling

`DataQualityProfiler` reports, per manifest:

- **dimensions** — row/column counts (+ entity/period counts when identifiable);
- **missingness** — per-column null counts/ratios and an overall ratio;
- **duplicates** — full-row duplicate count/ratio (+ key duplicates when entity
  and time columns are known);
- **temporal coverage** — min/max/distinct of the time column, when present;
- **quality warnings** — structured `QualityWarning`s with stable codes:
  `COLUMN_ALL_NULL`, `HIGH_MISSINGNESS`, `CONSTANT_COLUMN`, `DUPLICATE_ROWS`,
  `DUPLICATE_KEYS`, `SINGLE_ROW`.

## Fingerprint

Content-addressed: identical file contents — and the same content stored as CSV,
as Parquet, or held in memory — all produce the same `sha256:…` fingerprint.
Different content produces a different fingerprint. See
`tests/agentic/test_adapter_architecture.py`.

## Structured failures

| Situation | Error / code |
|---|---|
| missing `path` param | `UnsupportedSourceError` / `UNSUPPORTED_SOURCE` |
| unsupported extension (e.g. `.xlsx`) | `UnsupportedSourceError` / `UNSUPPORTED_SOURCE` |
| file does not exist | `SourceNotFoundError` / `SOURCE_NOT_FOUND` (also `FileNotFoundError`) |
| unparseable/empty-bytes file | `MalformedDatasetError` / `MALFORMED_DATASET` |
| header only, no rows | `EmptyDatasetError` / `EMPTY_DATASET` |

## Example

```python
from agentic.adapters import LocalTabularAdapter, AdapterRequest

m = LocalTabularAdapter().build_manifest(
    AdapterRequest(parameters={"path": "fixtures/sales.parquet", "time_field": "month"})
)
m.available_fields()        # ['region', 'month', 'units', 'revenue']
m.fingerprint               # 'sha256:…'
m.temporal_coverage.field   # 'month'
[w.code for w in m.quality_warnings]
```

## Dependencies

Parquet support requires `pyarrow` (declared in `requirements-dev.txt` for the
adapter tests). CSV support needs only pandas.

## In-memory sibling

`InMemoryDatasetAdapter` shares the same generic profiling for already-materialized
data (a DataFrame, a list of API records, or a `DocumentRecord` collection),
supplied at construction. It is the primary adapter for tests and in-process
pipelines and demonstrates the relational/API-records and document modalities.
