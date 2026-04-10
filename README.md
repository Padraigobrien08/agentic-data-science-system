# Agentic data science — EDGAR pipeline

This repo pulls **SEC EDGAR XBRL company facts**, normalizes them into a **quarterly panel**, engineers **metric features**, and scores **self-relative and peer-relative** unusual moves. Outputs are tabular artifacts (panel, features, anomalies, peer signals, trend-break hints) plus a **unified findings** table and a **Markdown report**. A thin **orchestration** layer turns a ticker list and short natural-language goal into a fixed **MCP tool** sequence; there is no LLM in the numerical path.

**MCP** exposes the same steps for Cursor/CLI; **evaluation** holds JSON-defined benchmark cases (fixtures and optional live stubs) with deterministic checks. All of that lives under `edgar_project/`; Phase 1 numerics remain in `src/` and `main.py`.

## Example outputs (static)

Browse [`examples/`](examples/) for **small, labeled samples** you can open without running anything: `report.example.md`, `unified_findings.example.csv`, `evaluation_summary.example.json`, `evaluation_results.example.json`, and `cli_run_digest.example.txt`. They are **not** produced by the pipeline and do not replace artifacts under `data/` — see [`examples/README.md`](examples/README.md).

**Where real files land:** [`data/README.md`](data/README.md) explains `data/raw/`, `data/processed/`, `data/artifacts/`, and `data/evaluation/` so you can tell pipeline output from benchmark output.

## Quick demo (skim + run, ~2 minutes)

**Offline (no SEC, ~seconds)** — exercises the analytical stack on versioned CSV fixtures:

```bash
cd <your-repo-clone>
PYTHONPATH=. python3 -m edgar_project.cli demo --fixtures
```

**What you should see:** A labeled block for benchmark outputs under `data/evaluation/` (suite JSON + per-case folders), then a tip pointing at `data/README.md`. Same fixture suite as `python3 -m edgar_project.cli evaluate`.

**Benchmarks only (no `demo`):** `PYTHONPATH=. python3 -m edgar_project.cli evaluate` — short pass/fail summary and paths to `*_results.json`.

**Live (network, SEC + cache)** — curated tickers and goals from `edgar_project/demo/scenarios.json`:

```bash
PYTHONPATH=. python3 -m edgar_project.cli demo --list
PYTHONPATH=. python3 -m edgar_project.cli demo
# or:  python3 -m edgar_project.cli demo retail_peers
```

**What you should see:** A **run digest** (status, tickers, output layout, primary file paths, counts, top unified findings). Then scenario-specific bullets. Use `demo -v` for the full artifact list, tool chain, and resolved tickers on stdout; orchestration **INFO** logs go to stderr.

**Why it’s worth a look**

- Fixture demo proves the **same detection code** you ship runs on **controlled inputs** with regression-style checks.
- Live demo shows **peer vs self** signals, **trend-break overlap** metadata, and **one narrative report** without opening every CSV.
- **Data quality / coverage** artifacts make missingness explicit alongside flags.
- **Orchestration** is deterministic rule-to-plan mapping over MCP tools (inspectable, no black-box scoring).

## CLI reference

From repo root (`PYTHONPATH=.`):

```bash
python3 -m edgar_project.cli run --tickers AAPL MSFT --goal "find unusual financial changes"
python3 -m edgar_project.cli evaluate
python3 -m edgar_project.cli evaluate --suite edgar_project/evaluation/benchmarks/suite_orchestration_mocked_v1.json
```

`evaluate` defaults to the offline fixture suite; prints case counts, failing IDs, and paths to JSON. Use `evaluate -v` for an extended table. `run -v` / `run --json` — orchestration logs or full `OrchestrationOutput`. `main.py` is unchanged.

## Notebook demo

Interactive walkthrough (fixture run, tables, one bar chart): open [`notebooks/demo_edgar_pipeline.ipynb`](notebooks/demo_edgar_pipeline.ipynb). From the repo root:

```bash
pip install jupyter matplotlib
jupyter notebook notebooks/demo_edgar_pipeline.ipynb
```

Uses the same offline fixture suite as `demo --fixtures` — no SEC credentials required.

## Manual validation (spot checks)

To record that extracted metrics were checked against SEC sources, use **`validation/README.md`**, append rows to **`validation/manual_validation.csv`**, and optionally keep notes in **`validation/manual_validation.md`**.

- **Templates & guide:** `validation/template/` (`manual_validation_template.csv`, `HOW_TO_FILL.md`)
- **Unverified candidates** (from current `panel.csv`): `validation/examples/candidates_from_artifacts_unverified.csv` — not SEC-confirmed until you fill `expected_value` and status.

Print candidate rows and companyfacts URLs:

```bash
python3 -m src.manual_validation --panel data/processed/panel.csv --max-rows 20
```

See **`validation/README.md`** for the column schema and workflow details.
