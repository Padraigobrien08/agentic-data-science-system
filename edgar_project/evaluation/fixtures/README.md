# Fixtures

This directory contains deterministic, version-controlled benchmark assets.

## Layout

- `cases/` benchmark case intent and scenario notes.
- `data/` synthetic or controlled input tables used instead of live SEC responses.
- `expected/` expected outputs/artifacts for deterministic regression checks.
- `benchmark_case.template.json` starter template for new fixture-first case definitions.

## Principles

- Keep files small and reviewable in git diffs.
- Prefer CSV/JSON with stable field ordering.
- Avoid generated timestamps and environment-dependent content.
- Make each fixture map to one explicit benchmark objective.
