# Agentic data science — EDGAR pipeline

Phase 1 ingests SEC XBRL company facts, builds a quarterly panel, computes features, and flags anomalies. Orchestration and MCP tools live under `edgar_project/`.

## Manual validation (spot checks)

To record that extracted metrics were checked against SEC sources, use **`validation/README.md`**, append rows to **`validation/manual_validation.csv`**, and optionally keep notes in **`validation/manual_validation.md`**.

- **Templates & guide:** `validation/template/` (`manual_validation_template.csv`, `HOW_TO_FILL.md`)
- **Unverified candidates** (from current `panel.csv`): `validation/examples/candidates_from_artifacts_unverified.csv` — not SEC-confirmed until you fill `expected_value` and status.

Print candidate rows and companyfacts URLs:

```bash
python -m src.manual_validation --panel data/processed/panel.csv --max-rows 20
```

See **`validation/README.md`** for the column schema and workflow details.
