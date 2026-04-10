# Evaluation and benchmarks

Deterministic checks over the analytical stack and (optionally) the orchestration entrypoint. Suites are JSON manifests; the runner executes cases and writes JSON summaries under the suite’s `output_dir` (default **`data/evaluation/`** — benchmark-only; see repo **`data/README.md`** vs **`data/artifacts/`** for live pipeline output).

## Benchmark layers

Execution path depends on `input.mode` (see below). When a case runs, checks stack as follows:

| Layer | Module / hook | What it asserts |
|--------|----------------|-----------------|
| **Artifacts** | `artifact_checks` | Required logical keys exist (paths optional for mocks), row counts, optional CSV column schemas vs `src` definitions, `enforce_schema` / `schema_exempt_keys`. |
| **Findings** | `analytical_checks` + runner-derived counts | Finding types/categories, totals and min counts, top-`n` slice constraints, overlap / caveat rules from `ExpectedFindings`. |
| **Metrics** | `runner._check_expected_metrics` | `expected_metrics` ranges (e.g. `runtime_seconds`, `findings_total`) and `max_runtime_seconds` on the case. |
| **Orchestration (mocked)** | `orchestration_checks` | `OrchestrationOutput` vs `ExpectedOrchestration` when `mode` is `orchestration_mocked` (tool sequence, status, artifact keys). |
| **Regression goldens** | `regression_snapshot` | Optional sparse JSON subset match after fixture runs (`regression_golden.golden_json_path`). See `fixtures/regression/README.md`. |
| **Rubric** | `rubric` | Loaded by the CLI; the runner stores it but **does not** currently apply rubric scores to pass/fail. |

Qualitative strings on the case (`qualitative_expectations`, `expected_findings.qualitative_expectations`, artifact `qualitative_checks`) are **recorded** on results for humans and reports; they are not automatically verified by code.

### Schema coupling to `src`

When `expected_artifacts.enforce_schema` is true, `artifact_checks.REQUIRED_COLUMNS_BY_ARTIFACT_KEY` is built from column tuples exported by `src` modules (e.g. `UNIFIED_FINDINGS_COLUMNS`, `ANOMALY_OUTPUT_COLUMNS`). Renaming or dropping columns in production code will fail benchmarks until manifests or the mapping are updated—this is intentional shared contract, not a duplicate schema DSL.

## Fixture-based vs live benchmarks

- **`fixture`** — Runs `src.*` helpers on CSVs from `input.fixture_paths` (e.g. `features_csv`, optional `trend_break_signals_csv`). Writes per-case artifacts under `<output_dir>/<suite_id>/<case_id>/`. Fully implemented; no SEC or MCP.
- **`orchestration_mocked`** — Runs `run_analysis_agent` with patched MCP tools (`orchestration_mocks`). Validates coordinator behavior and declared outputs without live SEC.
- **`live` / `hybrid`** — **Not implemented** for analytical execution. Cases with these modes are **skipped** with an explicit message (reserved for future pipeline/MCP integration).

## What is being evaluated

- **Contract and shape**: artifact keys, file presence (where required), CSV shape vs expected columns, row bounds.
- **Analytical outputs on controlled data**: unified findings table (types, categories, overlap metadata, caveats) and related anomaly/trend inputs as specified per case.
- **Performance envelope**: optional runtime and count ranges.
- **Coordinator mocks**: orchestration status, tool calls, and artifact map shape—not LLM quality.
- **Selected regressions**: compact fingerprints (category distributions, overlap summary, trust-artifact flags, data-quality categories) where `regression_golden` is set.

This is **not** end-to-end validation against real EDGAR responses unless you add and implement a live/hybrid runner path.

## How to run

**CLI (short summary on stdout):**

```bash
PYTHONPATH=. python3 -m edgar_project.cli evaluate
```

**Script (same runner, more flags by default):**

```bash
PYTHONPATH=. python3 edgar_project/evaluation/scripts/run_suite.py \
  --suite edgar_project/evaluation/benchmarks/suite_fixtures_v1.json
```

Useful flags:

- `--rubric` — Rubric JSON (default under `fixtures/`).
- `--write-markdown` — Also writes `<suite_id>_report.md` under `output_dir`.
- `--quiet` — Less console noise.
- `--update-regression-goldens` — Overwrites golden JSON for cases that define `regression_golden` (use only when intentionally updating baselines).

Outputs:

- `<output_dir>/<suite_id>_results.json` — Per-case status, messages, `checks`, metadata.
- `<output_dir>/<suite_id>_summary.json` — Aggregate counts and failure briefs.

Exit code **1** if any case is `failed` or `error`.

Programmatic use: `BenchmarkSuite.model_validate_json(...)`, `EvaluationRunner(suite=..., update_regression_goldens=...)`, `run_suite()`.

## Adding a new benchmark case

1. **Inputs** — Add CSVs under `fixtures/data/` (and `fixtures/expected/` if you compare to frozen expected tables elsewhere; the runner’s primary checks use `ExpectedArtifacts` / `ExpectedFindings`, not automatic full-file diff of every CSV).
2. **Manifest** — Add a `BenchmarkCase` object to a suite JSON under `benchmarks/` (copy structure from `suite_fixtures_v1.json`). Required pieces:
   - Stable `case_id`, `input.mode`, `input.fixture_paths.features_csv` for fixture mode.
   - `expected_artifacts` (`required_keys`, `items` with `min_rows` / schema behavior).
   - `expected_findings` when you care about types, categories, overlap, caveats, top slice.
   - `expected_metrics` for runtime bounds if needed.
3. **Template** — `fixtures/benchmark_case.template.json` is a starting sketch; align field names with live suites (`features_csv` not legacy `panel_csv` unless you implement it).
4. **Regression** — If the case should lock a compact fingerprint, add `regression_golden` and a file under `fixtures/regression/`, then follow `fixtures/regression/README.md`.

Re-run the suite locally before committing manifest + fixture changes.

## What results prove — and do not prove

**A passing suite shows** that, for the declared cases and modes:

- Produced artifacts meet the configured structural and row-count expectations (and schema enforcement where enabled).
- Unified findings (and related checks) satisfy the numeric and structural rules in `ExpectedFindings`.
- Mocked orchestration cases match their expected tool/output contracts.
- Optional regression goldens match the current compact blob.

**It does not show** that:

- Real SEC data, rate limits, or MCP failures behave correctly (`live`/`hybrid` not executed).
- Natural-language explanations are correct, complete, or useful (no LLM-as-judge in the default path).
- The system is free of bugs outside the scenarios and assertions you encoded.
- Production ranking, calibration, or business metrics are optimal.

Treat benchmarks as **regression and contract tests on explicit scenarios**, not as proof of production readiness.

## Related paths

- `benchmarks/README.md` — Suite file conventions.
- `fixtures/README.md` — Fixture directory layout.
- `fixtures/cases/README.md` — Scenario notes for humans.
