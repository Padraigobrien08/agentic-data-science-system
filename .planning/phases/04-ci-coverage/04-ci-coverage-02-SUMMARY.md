---
phase: 04-ci-coverage
plan: 02
subsystem: frontend
tags: [ci-coverage, playwright, browser, fixture, docker]
requires: [04-01]
provides:
  - Playwright auth/setup and narrow authenticated run-workflow regression
  - Deterministic seeded admin/project/run/artifact fixture for browser CI
  - Full-stack workflow wiring for fixture seeding, Node 20 setup, Playwright install, and artifact upload
affects: [frontend, github-actions, docker, browser-tests]
key-files:
  created: [frontend/playwright.config.ts, frontend/tests/e2e/auth.setup.ts, frontend/tests/e2e/fixture.ts, frontend/tests/e2e/run-workflows.spec.ts, tests/support/__init__.py, tests/support/seed_fullstack_browser_fixture.py]
  modified: [frontend/package.json, frontend/package-lock.json, frontend/.gitignore, .github/workflows/compose-smoke.yml, Dockerfile, .dockerignore]
requirements-completed: [QUAL-01, QUAL-02]
completed: 2026-04-17
---

# Phase 4 Plan 02: Browser Coverage Summary

## Accomplishments

- Added a dedicated Playwright harness with a reusable admin auth setup, storage-state reuse, and a focused authenticated spec for run answer, deep dive, and artifact-content delivery.
- Added a deterministic browser fixture seeder that upserts the smoke admin, creates a project and completed run, attaches a persisted markdown artifact, and emits the exact `admin_email`, `admin_password`, `project_id`, `run_id`, and `artifact_id` JSON payload the browser tests consume.
- Extended the `Full Stack` workflow to seed the fixture inside the live API container, install Node 20 and Chromium, run the browser suite, and upload fixture plus Playwright diagnostics.
- Included `tests/support/` in the backend image so the workflow’s `docker compose exec -T api python -m tests.support.seed_fullstack_browser_fixture` path works inside the container rather than only on the host checkout.

## Task Commits

1. `0393887` `test(04-02): add playwright browser harness`
2. `7db6018` `ci(04-02): wire seeded browser flow into full-stack gate`

## Verification

- `python3 -m py_compile tests/support/seed_fullstack_browser_fixture.py`
- `cd frontend && npm run test:e2e -- --list`
- `./scripts/smoke-compose.sh`
- `docker compose exec -T api python -m tests.support.seed_fullstack_browser_fixture`
- `cd frontend && PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 E2E_FIXTURE_PATH=/Users/padraigobrien/agentic_data_science_system/.tmp/e2e-fixture.json npm run test:e2e`

Result: the seeded browser flow passed locally with `2 passed`.

## Deviations From Plan

- The initial browser spec used a generic `Deep dive` link selector that was too broad for the real page. The final spec now loads the trace route directly, which stays within the plan’s allowed `clicks or loads the Deep dive route` behavior and removes selector ambiguity.
- Local Playwright execution required downloading the Chromium runtime and rerunning outside the sandbox because the desktop sandbox blocked browser launch.
