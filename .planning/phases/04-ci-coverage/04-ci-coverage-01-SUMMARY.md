---
phase: 04-ci-coverage
plan: 01
subsystem: ci
tags: [ci-coverage, full-stack, compose, smoke, secure-defaults]
requires: []
provides:
  - PR-triggered `Full Stack` workflow for the documented Compose stack
  - Secure-default smoke coverage for bootstrap-admin and ops-token routes
  - Alembic head merge so `docker compose up -d --build` can boot the stack
affects: [github-actions, docker-compose, alembic, auth, smoke]
key-files:
  created: [alembic/versions/009_merge_ci_heads.py]
  modified: [scripts/smoke-compose.sh, .github/workflows/compose-smoke.yml]
requirements-completed: [QUAL-01]
completed: 2026-04-17
---

# Phase 4 Plan 01: Full-Stack Smoke Summary

## Accomplishments

- Replaced the old API-only smoke path with a secure-default contract that checks `db`, `migrate`, `api`, `worker`, and `web`, authenticates through `POST /v1/auth/bootstrap` plus `POST /v1/auth/login`, and validates `/metrics` plus `/v1/worker/health` with the ops bearer token.
- Promoted the Compose workflow into a PR-triggered `Full Stack / full-stack` job with deterministic CI credentials, full-stack boot, and failure-path diagnostics upload.
- Fixed a real boot blocker in the documented stack by adding the missing Alembic merge revision for `008_user_admin_bootstrap` and `006_job_claim_token`, so `alembic upgrade head` now succeeds under Compose.

## Task Commits

1. `34bcb05` `ci(04-01): harden secure-default smoke contract`
2. `9d962ec` `ci(04-01): require full-stack compose smoke`

## Verification

- `docker compose up -d --build` with explicit CI-style `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`, and `EDGAR_BACKEND_OPS_API_TOKEN`
- `./scripts/smoke-compose.sh`

Result: smoke passed against the live stack after the Alembic merge-head fix.

## Deviations From Plan

- The stack could not satisfy the plan’s required smoke command until a missing Alembic merge revision was added. That migration fix is now part of the plan output because the full-stack CI gate would otherwise fail on every run before application health checks began.
- The smoke script needed `docker compose ps -a -q migrate` rather than `docker compose ps -q migrate` so it can inspect the one-shot exited migration container correctly.
