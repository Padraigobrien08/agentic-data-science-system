---
phase: 04-ci-coverage
plan: 03
subsystem: worker
tags: [ci-coverage, postgres, regressions, checkpoint]
requires: []
provides:
  - Shared Postgres regression runner for overlap and lease tests
  - Dedicated `Postgres Regressions / postgres-regressions` workflow
affects: [github-actions, postgres, worker, queue]
key-files:
  created: [.github/workflows/postgres-regressions.yml, .planning/phases/04-ci-coverage/04-ci-coverage-03-SUMMARY.md]
  modified: [scripts/ci-postgres-regressions.sh, .planning/STATE.md]
requirements-completed: [QUAL-03]
status: human_needed
completed: 2026-04-17
---

# Phase 4 Plan 03: Postgres Regression Summary

## Accomplishments

- Added `scripts/ci-postgres-regressions.sh` as the shared regression command for overlap isolation, worker heartbeat, and Postgres claim/reclaim locking.
- Added a dedicated PR workflow named `Postgres Regressions` with a real `postgres:16` service container, the exact `EDGAR_TEST_POSTGRES_URL` contract used by the tests, `set -o pipefail`, and failure-log artifact upload.

## Task Commits

1. `c16d875` `chore(04-ci-coverage-03): add postgres regression runner`
2. `aeba0a9` `ci(04-03): add postgres regression workflow`

## Verification

- `bash -n scripts/ci-postgres-regressions.sh`
- `EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:55432/edgar bash scripts/ci-postgres-regressions.sh`

Result: the focused regression slice passed locally with `6 passed`.

## Pending Human Action

This plan is waiting on the repository-settings checkpoint from the plan file. After the new workflows are pushed and have run at least once on GitHub, mark these exact checks as required for merge:

- `Full Stack / full-stack`
- `Postgres Regressions / postgres-regressions`

Reply `done` after that settings change is in place so Phase 4 can be closed out.
