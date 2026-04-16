---
phase: 04
slug: ci-coverage
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-16
---

# Phase 04 - Validation Strategy

> Per-phase validation contract for CI coverage and browser-flow hardening.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` + `Vitest` + `Playwright` |
| **Config file** | `pytest.ini`, `frontend/vitest.config.ts`, `frontend/playwright.config.ts` (new in this phase) |
| **Quick run command** | `EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar python3 -m pytest tests/test_run_isolation_overlap.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle_postgres.py -q --tb=short` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short && (cd frontend && npm run test && npm run build) && docker compose up -d --build && ./scripts/smoke-compose.sh && (cd frontend && npx playwright test)` |
| **Estimated runtime** | ~30 seconds quick, ~8-12 minutes full |

## Sampling Rate

- **After every task commit:** run the task-local `<automated>` command from the active plan
- **After every plan wave:** rerun the requirement-specific command for the completed plan plus `cd frontend && npm run build` when web or Playwright wiring changes
- **Before `$gsd-execute-phase 4` completion:** full suite green plus the final targeted Postgres slice and full-stack browser gate
- **Max feedback latency:** 30 seconds for targeted regressions

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01 | 01 | 1 | QUAL-01 | full-stack integration + CI | `docker compose up -d --build && ./scripts/smoke-compose.sh` | ❌ | ⬜ pending |
| 04-02 | 02 | 2 | QUAL-02 | browser/e2e + frontend integration | `(cd frontend && npx playwright test tests/e2e/run-workflows.spec.ts)` | ❌ | ⬜ pending |
| 04-03 | 03 | 3 | QUAL-03 | Postgres integration + CI regression | `EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar python3 -m pytest tests/test_run_isolation_overlap.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle_postgres.py -q --tb=short` | ⚠ partial | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky/partial*

## Wave 0 Requirements

- [ ] `frontend/playwright.config.ts` - Playwright config, retries, reporters, and base URL
- [ ] `frontend/tests/e2e/auth.setup.ts` - bootstrap-admin login and stored auth state
- [ ] `frontend/tests/e2e/run-workflows.spec.ts` - narrow authenticated flow for sign-in, run answer, deep dive, and artifact delivery
- [ ] `tests/support/seed_fullstack_browser_fixture.py` - deterministic completed-run fixture seeding inside the running stack
- [ ] `.github/workflows/ci.yml` - add required `postgres-regressions` and `full-stack` jobs
- [ ] `scripts/smoke-compose.sh` - secure-default bootstrap/admin and ops-token verification instead of open-registration assumptions
- [ ] `cd frontend && npm install -D @playwright/test@1.59.1 && npx playwright install --with-deps chromium`

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| GitHub branch protection or rulesets treat the new full-stack and Postgres regression jobs as required PR checks | QUAL-01, QUAL-03 | Required-check enforcement lives in GitHub settings, not in repo files | 1. Open the repository branch protection or ruleset for the protected default branch. 2. Confirm the final CI job names for the full-stack gate and Postgres regression slice are marked required. 3. Open a test PR and verify merge is blocked when either required job fails. |

## Validation Sign-Off

- [x] All planned tasks have automated verification commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 names the missing Playwright, fixture, and CI wiring references
- [x] No watch-mode commands
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
