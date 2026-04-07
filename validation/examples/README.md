# Example / candidate rows (not validated)

Files here support **getting started** with manual validation. Nothing in this folder counts as a successful or peer-reviewed SEC check unless you complete it and copy results into `../manual_validation.csv` with an honest `validation_status`.

| File | Meaning |
|------|---------|
| `candidates_from_artifacts_unverified.csv` | **Snapshot** of a few `(ticker, cik, period, metric, extracted_value)` rows produced from `data/processed/panel.csv` at generation time. **`expected_value` is empty** — you must fill it from companyfacts or filings. Values are **not** confirmed against the SEC in this repo. |
| `ticker_map_for_candidates.csv` | Optional `ticker,cik` map passed to `python -m src.manual_validation --ticker-map …` when generating candidates. |

## Regenerate candidates

After refreshing the panel:

```bash
python -m src.manual_validation --panel data/processed/panel.csv \
  --metrics revenue,net_income --max-rows 8 \
  --ticker-map validation/examples/ticker_map_for_candidates.csv \
  --output-csv validation/examples/candidates_from_artifacts_unverified.csv
```

Committing regenerated files is optional; they are **convenience samples**, not audit evidence.
