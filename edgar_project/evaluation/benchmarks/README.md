# Benchmarks

Framework overview (layers, modes, how to run, limitations): see [`../README.md`](../README.md).

This directory stores inspectable benchmark suite manifests.

- Prefer small, high-value deterministic cases.
- Keep suite files in JSON for easy diff/version review.
- Avoid embedding runtime-generated artifacts here.

Suggested file naming:

- `suite_smoke.json`
- `suite_fixtures_v1.json`
- `suite_regression_core.json`

Current fixture-first baseline:

- `suite_fixtures_v1.json` (five controlled deterministic scenarios; no live SEC dependency)
