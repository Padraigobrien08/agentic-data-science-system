# Validation templates (not live records)

Use these files to **start** a validation workflow. They are **not** evidence of successful checks.

| File | Purpose |
|------|---------|
| `manual_validation_template.csv` | Column layout + one **synthetic** example row (clearly non-real period). Copy or merge into your team’s real CSV when ready. |
| `HOW_TO_FILL.md` | Step-by-step guide for each column. |

Authoritative schema reference: `src.manual_validation.VALIDATION_COLUMNS` and `../README.md`.

Real, append-only records belong in **`../manual_validation.csv`** (repository root under `validation/`), not in this folder.
