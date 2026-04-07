# Manual validation (spot checks)

Durable **validation records** live in `manual_validation.csv` (append-only). Helpers under `src/manual_validation.py` emit **candidate rows** from `data/processed/panel.csv` so reviewers can copy values, compare to SEC sources, and record outcomes. This is **not** automated reconciliation.

**Quick start:** open `template/HOW_TO_FILL.md`, copy column layout from `template/manual_validation_template.csv`, and optionally start from `examples/candidates_from_artifacts_unverified.csv` (pipeline snapshot only — **not** SEC-verified).

## Repository layout

| Location | Purpose |
|----------|---------|
| **`manual_validation.csv`** (this directory) | **Live append-only store** for real validation rows you choose to keep in-repo. |
| **`template/`** | Starter CSV + **HOW_TO_FILL.md** — includes one **synthetic** example row (not real SEC data). |
| **`examples/`** | **Unverified** candidate rows exported from `data/processed/panel.csv` for convenience (`candidates_from_artifacts_unverified.csv`). Not evidence until completed. |
| `manual_validation.md` | Optional session notes (structured data stays in CSV). |
| `metric_mapping.csv` | Canonical metric → XBRL tag mapping (generated from code). |

## Artifacts

| File | Purpose |
|------|---------|
| `manual_validation.csv` | **Canonical store** — one row per validation record; append new rows over time. |
| `manual_validation.md` | Optional session notes / checklist (structured data stays in the CSV). |
| `metric_mapping.csv` | Canonical metric → XBRL tag mapping (generated from code). |

## Validation record schema (`manual_validation.csv`)

Stable columns (in order):

| Column | Description |
|--------|-------------|
| `ticker` | Symbol (optional if unknown). |
| `cik` | SEC CIK (integer, as in the panel). |
| `period` | Fiscal period key, e.g. `2023-Q1`. |
| `metric` | Pipeline metric name (`revenue`, `net_income`, … — see `METRIC_COLUMNS` in `src/normalization.py`). |
| `extracted_value` | Value from the pipeline artifact at review time (usually `data/processed/panel.csv`). |
| `expected_value` | Value from the SEC source (companyfacts `val` or filing) after you locate the matching fact. |
| `source_reference` | Where you looked: e.g. `companyfacts us-gaap/Revenues USD`, accession, or URL. |
| `checked_by` | Initials or handle. |
| `checked_date` | ISO date `YYYY-MM-DD`. |
| `validation_status` | Team convention; e.g. `pass`, `fail`, `needs_review`. |
| `notes` | Discrepancy, rounding, follow-up. |

Initialize or repair an empty file with the correct header:

```bash
python -c "from src.manual_validation import ensure_validation_csv; ensure_validation_csv()"
```

Legacy CSVs without `expected_value` still load: the column is added when reading.

## How to perform a spot check

1. **Build the panel** — run the Phase 1 pipeline so `data/processed/panel.csv` exists.
2. **Emit candidates** — print a short table + companyfacts URLs:

   ```bash
   python -m src.manual_validation --panel data/processed/panel.csv --max-rows 20
   ```

   Or write a **prefilled CSV** (full schema; fill `expected_value` and the rest after review):

   ```bash
   python -m src.manual_validation --panel data/processed/panel.csv \
     --max-rows 15 --output-csv validation/candidates_last_run.csv
   ```

   Optional **ticker** column on candidates (two-column CSV `ticker,cik`):

   ```bash
   python -m src.manual_validation --ticker-map validation/ticker_map.csv \
     --output-csv validation/candidates_last_run.csv
   ```

3. **Open SEC data** for each CIK — use URLs printed by the CLI, or cached JSON under `data/raw/`. Match **us-gaap** tag, **USD**, **form** (10-K/10-Q), **fp** (Q1–Q4), **fy**. Tag priority: `src/metric_mapping.py` / `docs/metric_mapping.md`.
4. **Compare** — set `expected_value` from the source fact; set `extracted_value` from the panel if you are recording a fresh check (they may match).
5. **Append a completed row** to `manual_validation.csv` (or merge from your candidate export after editing).

## Scope

- Sampling only (a few companies × periods × metrics) is enough for regression confidence.
- No browser automation, bulk diffing, or scoring.

## Python helpers

```python
from src.manual_validation import (
    VALIDATION_COLUMNS,
    candidate_records_from_panel,
    ensure_validation_csv,
    load_validation_records,
    companyfacts_url,
    panel_to_long,
)
```
