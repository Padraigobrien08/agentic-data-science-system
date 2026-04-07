# How to fill in manual validation records

Use the canonical columns in order (same as `manual_validation_template.csv` and `../manual_validation.csv`).

## Before you start

1. Build or refresh `data/processed/panel.csv` (Phase 1 pipeline).
2. Optionally emit **candidates** (prefilled `extracted_value` only):

   ```bash
   python -m src.manual_validation --panel data/processed/panel.csv \
     --metrics revenue,net_income --max-rows 15 \
     --output-csv validation/examples/candidates_from_artifacts_unverified.csv
   ```

3. Open SEC **companyfacts** for each CIK (URLs print with the text output, or use `config.SEC_COMPANYFACTS_URL`).
4. Match **us-gaap** tag, **USD**, **form** (10-K/10-Q), **fy**, **fp** per `docs/metric_mapping.md`.

## Column-by-column

| Column | What to enter |
|--------|----------------|
| **ticker** | Symbol if known; optional. |
| **cik** | Integer CIK (must match the panel). |
| **period** | Fiscal key `YYYY-Qn` as in the panel (e.g. `2023-Q1`). |
| **metric** | Pipeline name: `revenue`, `net_income`, etc. (`METRIC_COLUMNS` in `src/normalization.py`). |
| **extracted_value** | Number from `panel.csv` at the time you review (copy from candidate export or panel). |
| **expected_value** | Number from the SEC fact you accept as the reference (`val` in JSON, or filing). |
| **source_reference** | Traceability: e.g. `companyfacts us-gaap/Revenues USD`, accession `0000320193-24-000077`, or filing URL. |
| **checked_by** | Your initials or handle. |
| **checked_date** | ISO date `YYYY-MM-DD`. |
| **validation_status** | Team convention; e.g. `pass`, `fail`, `needs_review`. Do **not** mark `pass` until you have compared source vs extracted. |
| **notes** | Rounding, restatements, which tag won if multiple, follow-ups. |

## Unverified / in progress

Use **`needs_review`** or leave **`validation_status`** empty until the comparison is done. Never imply SEC sign-off you have not performed.

## Where to store completed rows

Append to **`validation/manual_validation.csv`** (or your team’s chosen path). Keep **`validation/template/`** for blanks and examples only; do not treat the template example row as a real validation.
