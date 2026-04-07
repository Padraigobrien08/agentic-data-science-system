# Manual validation (spot checks)

Lightweight, developer-facing workflow to record that specific extracted metrics were checked against SEC source data. This is **not** automated reconciliation: you open the official JSON (or filings) and confirm a few cells by hand.

## Artifacts

| File | Purpose |
|------|---------|
| `manual_validation.csv` | One row per validation record; **append** new rows over time. |
| `manual_validation.md` | Optional session notes / checklist (structured data stays in the CSV). |

### Record schema (`manual_validation.csv`)

| Column | Description |
|--------|-------------|
| `ticker` | Symbol (optional if you only have CIK). |
| `cik` | SEC CIK (integer as in the panel). |
| `period` | Fiscal period key, e.g. `2023-Q1`. |
| `metric` | Pipeline metric name: `revenue`, `net_income`, … (see `src/normalization.py` `METRIC_COLUMNS`). |
| `extracted_value` | Numeric value from `data/processed/panel.csv` (or long melt) at validation time. |
| `source_reference` | Where you looked, e.g. `companyfacts us-gaap/Revenues USD FY2023 Q1`, filing accession, or filing URL. |
| `checked_by` | Initials or handle. |
| `checked_date` | ISO date `YYYY-MM-DD`. |
| `validation_status` | e.g. `pass`, `fail`, `needs_review`. |
| `notes` | Short explanation, discrepancy amount, or follow-up. |

## How to perform a spot check

1. **Produce or refresh the panel** (e.g. run the Phase 1 pipeline so `data/processed/panel.csv` exists).
2. **List candidate rows** to review (sorted long-format slice + SEC companyfacts URLs):

   ```bash
   python -m src.manual_validation --panel data/processed/panel.csv --max-rows 20
   ```

   Narrow metrics if needed:

   ```bash
   python -m src.manual_validation --metrics revenue,net_income --max-rows 15
   ```

3. **Open SEC data** for each CIK shown in the output. Use the printed `companyfacts` URL, or your cached JSON under `data/raw/` if you already fetched it. Find the relevant **us-gaap** tag and **USD** unit entry matching **form** (10-K / 10-Q), **fp** (Q1–Q4), and **fy** (fiscal year). Tag priority for each metric is defined in `src/metric_extraction.py` (`METRIC_TAGS`).
4. **Compare** the fact `val` (and period metadata) to `extracted_value`. Small float differences can occur from rounding; document in `notes` if material.
5. **Append a row** to `manual_validation.csv` with your conclusion.

## Scope

- No browser automation, scraping, or bulk diffing is required or provided here.
- Validation is **sampling**: a few periods × metrics × companies is enough for regression confidence between releases.

## Helper module

Import from code or tests:

```python
from src.manual_validation import (
    VALIDATION_COLUMNS,
    companyfacts_url,
    panel_to_long,
    format_candidate_table,
)
```
