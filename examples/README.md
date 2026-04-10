# Example outputs (static)

These files are **hand-authored or copied shapes** for documentation. They are **not** produced by running the pipeline in this clone and **must not** be confused with live outputs under `data/processed/`, `data/artifacts/`, or `data/evaluation/`.

| File | Purpose |
|------|---------|
| `report.example.md` | Shape of a generated Markdown report (short). |
| `unified_findings.example.csv` | Column layout and typical unified-finding rows (synthetic CIKs). |
| `evaluation_summary.example.json` | Shape of `*_summary.json` from benchmark runs. |
| `evaluation_results.example.json` | Shape of `*_results.json` (two fictional cases). |
| `cli_run_digest.example.txt` | Typical `python3 -m edgar_project.cli run` / `demo` stdout digest (no SEC run). |

To generate **real** artifacts, follow **Quick demo** in the root [`README.md`](../README.md).
