# Manual validation log (optional)

Structured **records** belong in **`manual_validation.csv`** (see `README.md` for the full schema). Use this file for session notes, checklists, or reminders.

## Session template

**Date:** YYYY-MM-DD  
**Reviewer:**  
**Panel / commit / inputs:**

- [ ] Generated candidates (`python -m src.manual_validation …` or `--output-csv`).
- [ ] Opened SEC companyfacts (or raw cache) per CIK.
- [ ] Filled `expected_value` and `source_reference` after matching tag / period / USD.
- [ ] Set `validation_status` and `notes` (rounding tolerances, discrepancies).

## Status values (suggested)

Examples: `pass`, `fail`, `needs_review`, `n/a` — align with your team.
