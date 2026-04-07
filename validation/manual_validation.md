# Manual validation log (optional)

Structured records belong in **`manual_validation.csv`** (same column names as the header row). Use this file for free-form session notes, checklist reminders, or follow-up items.

## Session template

**Date:** YYYY-MM-DD  
**Reviewer:**  
**Panel / commit / inputs:**

- [ ] Picked sample rows (CIK × period × metric) from `candidates` CLI output or `data/processed/panel.csv`.
- [ ] Opened SEC companyfacts JSON for each CIK (URL printed by the CLI or built from `config.SEC_COMPANYFACTS_URL`).
- [ ] Compared `extracted_value` to the appropriate us-gaap tag instance (form 10-K/10-Q, fiscal period, USD).
- [ ] Recorded outcomes in `manual_validation.csv` (`validation_status`, `notes`, `source_reference`).

## Status values (suggested)

Use any convention your team agrees on; examples: `pass`, `fail`, `needs_review`, `n/a`.
