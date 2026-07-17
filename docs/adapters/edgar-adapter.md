# EDGAR Adapter

`EDGARAdapter` (`agentic/adapters/edgar.py`, `adapter_id = "edgar"`) routes the
existing SEC EDGAR system through the input-adapter architecture **without
rewriting the deterministic pipeline**. It wraps and describes; it does not move
numerical computation. `EdgarInputAdapter` remains as a backward-compatible alias.

## Role in the platform

EDGAR stays: (1) a one-click demo, (2) a first-party adapter, (3) a reference
investigation template, and (4) a regression fixture. The deterministic layer in
`src/` and `edgar_project/` is untouched — the adapter reaches it (offline for
fixtures) and produces a `DatasetManifest` describing the EDGAR panel.

## Capabilities

| Field | Value |
|---|---|
| source types | `edgar`, `csv` |
| modalities | `tabular`, `time_series` |
| permitted ops | materialize, profile_schema, profile_quality, fingerprint, full_scan |
| temporal | yes (fiscal `period`) |
| entity ids | yes (`ticker`) |
| adapter version | `2` |

## Manifest sources

`build_manifest(request)` has two offline-safe paths:

- **Panel file** — `parameters["panel_csv"]`: the EDGAR panel CSV is materialized
  through `TabularFileMaterializer` and profiled. `provenance.parameters` records
  the `panel_csv` path for reproducibility.
- **Declared schema** — no panel supplied: the canonical EDGAR panel schema is
  declared via `SchemaOnlyMaterializer` (no data materialized, `row_count = None`),
  with `entities` taken from `request.entities` (upper-cased) or
  `config.DEFAULT_TICKERS`.

Live SEC materialization stays behind the existing MCP tooling; the adapter does
not fetch from the network to build a manifest, so fixture/regression runs are
fully deterministic and offline.

## Domain knowledge lives in hints, not the general layer

EDGAR specificity is injected as **hints** on the materialized dataset — the
general `SchemaProfiler`/`DataQualityProfiler` never learn EDGAR vocabulary:

| Column | role hint | semantic hint | unit |
|---|---|---|---|
| `ticker` | `entity_id` | `identifier` | — |
| `cik` | `identifier` | `identifier` | — |
| `company_name` | `dimension` | `categorical` | — |
| `period` | `time_index` | `temporal` | — |
| `revenue`, `net_income` | `metric` | `monetary` | USD |
| `revenue_growth_qoq`, `net_margin`, `debt_to_assets` | `metric` | `percentage` | ratio |
| `current_ratio` | `metric` | `real` | ratio |

Metric columns come from the pipeline's `src.anomaly.FEATURE_COLS` (offline
import), so the adapter stays truthful if that contract changes.

Because these are hints, the **same** `period`/`ticker`/`revenue` columns fed to
`LocalTabularAdapter` (no hints) are profiled generically — proving no EDGAR
assumptions leak into the shared layer.

## Manifest example (panel file)

```
DatasetManifest(
  name="EDGAR panel (…​.csv)", adapter_version="2", modality=time_series,
  source_identity=SourceIdentity(adapter_id="edgar", source_type="edgar", …),
  fingerprint="sha256:…",
  columns=[ ticker→entity_id, cik→identifier, period→time_index(temporal),
            revenue→metric(monetary,USD), net_margin→metric(percentage,ratio), … ],
  dimensions=DatasetDimensions(row_count=N, column_count=M, entity_count=…, period_count=…),
  temporal_coverage=TemporalCoverage(field="period", minimum=…, maximum=…),
  missingness=…, duplicates=…, quality_warnings=[…],
  provenance=DatasetProvenance(adapter_id="edgar", parameters={"panel_csv": "…"}),
)
```

## Behavioral compatibility

The pre-existing EDGAR adapter contract is preserved
(`tests/agentic/test_input_adapters.py`, still green): declared manifests
up-case requested tickers, expose `ticker` as the entity-id column and `period`
as the time-index column, include `revenue` among metric names, and report
`row_count = None`; the panel-CSV path assigns identifier/time-index/metric roles
and records `panel_csv` in provenance; a missing panel file raises a structured
`SourceNotFoundError` (still a `FileNotFoundError`). `EDGARAdapter` and the shared
`SchemaProfiler`/quality profiler additionally enrich the manifest with semantic
types, fingerprint, temporal coverage, missingness, duplicates, and warnings.

## Not changed

- No change to `src/` numerical logic or `edgar_project/mcp` tools.
- No wiring into production orchestration.
- The deterministic EDGAR regression tests (`tests/test_anomaly.py`,
  `tests/mcp/…`, orchestration) remain green.
