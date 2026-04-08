# EDGAR MCP layer (Phase 2)

Thin MCP surface over the Phase 1 pipeline (`main.py` and `src/`). Phase 1 stays runnable on its own; this package adds tools, schemas, and stdio MCP.

## MCP server (stdio)

Use this when wiring **Cursor**, **Claude Desktop**, or **MCP Inspector** to the repo.

From the **repository root**:

```bash
python -m edgar_project.mcp.server
```

Equivalent:

```bash
python -m edgar_project.mcp server
```

Logs go to stderr with timestamps. Each tool invocation logs a line like:

`mcp_tool_call name=resolve_company params={'ticker': 'AAPL'}`

## Local CLI (no MCP client)

Invoke the same tool functions directly; **JSON** (response envelope) prints on **stdout**; logs on **stderr**.

```bash
python -m edgar_project.mcp.cli resolve-company AAPL
python -m edgar_project.mcp.cli fetch-company-data MSFT
python -m edgar_project.mcp.cli build-panel AAPL MSFT --refresh
python -m edgar_project.mcp.cli compute-features --tickers AAPL
python -m edgar_project.mcp.cli compute-features --panel-csv data/processed/panel.csv
python -m edgar_project.mcp.cli detect-anomalies --tickers AAPL
python -m edgar_project.mcp.cli detect-anomalies --features-csv data/processed/features.csv
python -m edgar_project.mcp.cli generate-report --use-default
python -m edgar_project.mcp.cli run-pipeline --tickers AAPL
python -m edgar_project.mcp.cli run-pipeline --refresh
```

Suppress INFO logs (stderr); errors still surface:

```bash
python -m edgar_project.mcp.cli -q resolve-company AAPL
```

Put `-q` **before** the subcommand (e.g. `resolve-company`).

Same entrypoint (place ``-q`` before the subcommand name):

```bash
python -m edgar_project.mcp cli -q resolve-company AAPL
```

## Phase 1 artifact keys

Tool responses use `artifacts` (and optional `data` fields such as `data_quality_summary_path`, `exclusions_summary_path`, `peer_signals_path`, `trend_break_signals_path`, `unified_findings_path`, findings summary paths, metric coverage paths, `metric_caveats_extraction_path` / `metric_caveats_panel_path`, `manual_validation_path`) with role keys from `edgar_project.mcp.schemas`: `panel_csv`, `features_csv`, `anomalies_csv`, `report_md`, `data_quality_csv`, `exclusions_csv`, `peer_signals_csv`, `trend_break_signals_csv`, `unified_findings_csv`, `findings_summary_by_company_csv`, `findings_summary_by_metric_csv`, `findings_summary_by_period_csv`, `metric_coverage_summary_csv`, `metric_coverage_by_company_csv`, `metric_coverage_by_period_csv`, `metric_caveats_extraction_csv`, `metric_caveats_panel_csv`, and `manual_validation_csv` when `validation/manual_validation.csv` is present. After `run_pipeline` or `generate_report` with default Phase 1 paths, `data` may also include `trustworthiness_artifact_paths` (role → path), `trustworthiness_summary` (e.g. caveat row counts), and `combined_findings_count`. Orchestration merges `artifacts` into `artifact_paths` unchanged.

## Tests

```bash
pip install -r requirements-dev.txt
python -m pytest tests/mcp -v
```

## Dependencies

See repo root `requirements.txt` (`mcp`, `pydantic`, `requests`, …).
