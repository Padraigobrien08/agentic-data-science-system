# Regression goldens (sparse snapshots)

A few fixture cases declare `regression_golden.golden_json_path` in the suite JSON. After the analytical pipeline runs, the runner builds a **compact blob** (category counts, overlap summary, trust-artifact flags, optional data-quality fingerprint) and checks that every field in the golden JSON matches the live blob. Keys in the golden file are a **subset** of the actual output, so you can assert only what matters and avoid brittle full-table snapshots.

## When a check fails

Read the failure lines prefixed with `regression golden:` in the case message. They name the JSON path and expected vs actual values.

## Intentionally updating goldens

1. Confirm the behavioral change is intended (fixtures, `build_unified_findings`, category rules in `regression_snapshot.derive_finding_category_counts` / `EvaluationRunner._derive_finding_categories`, etc.).
2. Regenerate from a clean fixture run:

   ```bash
   python edgar_project/evaluation/scripts/run_suite.py \
     --suite edgar_project/evaluation/benchmarks/suite_fixtures_v1.json \
     --update-regression-goldens
   ```

   That overwrites each golden file with the **full** compact blob. Trim the file by hand if you want to keep only high-signal fields (counts, overlap flags, `trust_artifacts_present`, etc.).

3. Commit the edited JSON with a short note in the commit message about what changed.

## Adding a new golden

1. Add `regression_golden: { "golden_json_path": "edgar_project/evaluation/fixtures/regression/..." }` to the benchmark case.
2. Create an empty or minimal JSON, run once with `--update-regression-goldens`, then delete keys you do not want to lock.
