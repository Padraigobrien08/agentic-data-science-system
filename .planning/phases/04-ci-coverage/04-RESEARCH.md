# Phase 4: CI Coverage - Research

**Researched:** 2026-04-16
**Domain:** GitHub Actions CI coverage for the documented Docker Compose stack, authenticated browser flows, and Postgres-backed regression gating
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### PR gate shape
- **D-01:** CI should add a dedicated PR-required full-stack integration job for the documented `db + migrate + api + worker + web` stack while keeping the existing faster backend and frontend jobs.
- **D-02:** The full-stack gate should validate the documented Postgres-based deployment path, not replace all other CI with one slower monolith.

### CI auth posture
- **D-03:** CI must exercise the secure-default auth posture by using the bootstrap-admin token for operator setup and the ops token for `/metrics` and `/v1/worker/health`.
- **D-04:** CI must not relax security by enabling open registration or unauthenticated ops routes just to make integration checks easier.

### Frontend verification depth
- **D-05:** Authenticated frontend flows for sign-in, run answer, trace navigation, and artifact delivery should be covered by a narrow browser-level test flow rather than only unit tests or server-only route tests.

### Concurrency regression placement
- **D-06:** Collision, lease-expiry, and Postgres-specific worker regressions should be promoted to PR-required targeted test slices for faster and clearer failure isolation, not left only inside a slower full-stack or manual workflow.

### Claude's Discretion
- Exact workflow/job split, names, and whether the full-stack gate lives in `ci.yml` or a referenced workflow, as long as it is PR-required
- Exact CI env/secret injection mechanics for bootstrap and ops credentials
- Exact browser-test wiring, fixtures, and narrow path coverage, as long as the test remains focused on authenticated run workflows and artifact delivery
- Exact targeted regression subset promoted into required slices, as long as it covers the collision, lease, and Postgres queue risks called out by `QUAL-03`

### Deferred Ideas (OUT OF SCOPE)
None — discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| QUAL-01 | Pull request CI exercises the documented Postgres + API + worker + frontend stack instead of only a narrow backend subset | Add a required Docker Compose gate against `docker-compose.yml`, update smoke checks for secure-default auth, and run browser verification against the live web container |
| QUAL-02 | Authenticated frontend flows, artifact delivery, and run-trace navigation are covered by automated tests | Add Playwright with admin auth setup, a seeded completed run fixture, and a narrow spec covering sign-in, run answer, deep dive, and artifact proxy delivery |
| QUAL-03 | Concurrency, artifact-collision, and lease-expiry regressions are covered by automated tests | Promote existing overlap, heartbeat, and Postgres claim/reclaim tests into a required targeted pytest slice backed by a Postgres service container |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- Keep the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture; do not turn Phase 4 into a framework rewrite.
- Prefer explicit seams and incremental migrations over invasive refactors; reuse the current workflows, stack scripts, auth flow, and test helpers where possible.
- Preserve the deterministic `src/` analysis path; CI coverage for this phase should not depend on live SEC or optional LLM behavior.
- Avoid breaking existing run APIs, artifact access patterns, or documented local workflows unless the phase also supplies the migration path.
- Security defaults must stay safe in deployed environments; CI should validate bootstrap-admin and ops-token behavior, not bypass it.
- Health, metrics, and retained run data must reflect real system state; false-green CI checks are worse than noisy failures.
- Follow existing repo testing conventions: `pytest` for backend/integration tests, Vitest for frontend unit tests, semantic DOM assertions over snapshots, package-root Python imports, and `@/` frontend imports.
- No repo-local `.claude/skills/` or `.agents/skills/` directories were present, so there are no extra project skill rules to honor for this phase.

## Summary

Phase 4 should add truth to CI, not just more minutes. The current required workflow only runs backend `pytest` against SQLite and frontend `lint + build`, while the optional compose smoke still assumes pre-Phase-3 behavior: it starts only `db + migrate + api`, skips `worker` and `web`, creates a user via open registration, and hits worker health without the required ops token. That means the documented deployment path and the secure-default posture can still drift without failing pull requests.

The clean plan is to keep the existing fast jobs, add one required full-stack Docker Compose job that mirrors the documented `db + migrate + api + worker + web` stack, and add one required targeted Postgres pytest job for lease/collision regressions. Browser coverage should use Playwright, not a hand-rolled curl/assertion flow. The browser test should log in as a bootstrapped admin, because the run answer and deep-dive pages currently request admin-gated `include_payloads` data from the backend.

Do not execute a live EDGAR run inside the browser test. Seed a minimal completed run, steps, and artifact through existing backend models/services inside the running stack, then verify the real Next.js flow: sign-in, open run answer, navigate to deep dive, and fetch artifact content through the app proxy. That keeps the phase scoped to CI truthfulness rather than live SEC reliability.

**Primary recommendation:** Keep four PR-required checks: existing backend pytest, existing frontend lint/build, a new targeted Postgres regression slice, and a new secure-default full-stack Compose plus Playwright gate.

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| GitHub Actions | `ubuntu-latest` runners | PR-required workflow orchestration | Native CI surface already used by the repo and officially supports concurrency groups, service containers, and workflow artifacts |
| Docker Compose | `v2.20+` minimum (repo docs); local machine has `v5.1.1` | Truthful full-stack gate for `db + migrate + api + worker + web` | Mirrors `docker-compose.yml` and `docs/local-stack.md` instead of inventing a second integration stack |
| `@playwright/test` | `1.59.1` (published 2026-04-01) | Narrow browser coverage for sign-in, run answer, deep dive, and artifact delivery | Official Playwright CI/auth guidance matches this repo's server-rendered Next.js and secure auth flow |
| `pytest` | Repo line `>=8.0`; current upstream `9.0.3` (published 2026-04-07) | Targeted backend and Postgres regression slices | Existing tests already cover overlap, heartbeat, and queue-claim semantics; Phase 4 mainly needs CI promotion, not a test-runner swap |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| PostgreSQL service container | `postgres:16` / repo uses `postgres:16-alpine` | Fast Postgres-backed pytest job for `QUAL-03` | Use for targeted regression slices that need real Postgres semantics without booting the entire web stack |
| GitHub workflow artifacts | Official `upload-artifact` / `download-artifact` actions | Persist Playwright HTML reports, traces, and Docker logs | Use on failure in full-stack/browser jobs so regressions are diagnosable |
| Vitest | Repo uses `^2.1.9`; current upstream `4.1.4` (published 2026-04-09) | Keep existing frontend unit/component coverage | Retain as the fast frontend layer; it complements Playwright and should not be replaced in this phase |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Required fast jobs + targeted Postgres slice + required full-stack gate | One single monolithic full-stack workflow | Simpler file layout, but much worse failure isolation and slower PR feedback |
| Playwright | Cypress | Cypress would work for browser-only UI paths, but Playwright's official CI/auth/tracing guidance fits SSR Next.js flows and failure diagnostics better |
| Seeding completed runs through existing backend models/services | Test-only API endpoints | Test-only routes are faster to wire, but they weaken brownfield safety and create production-only surface area to maintain |

**Installation:**
```bash
cd frontend
npm install -D @playwright/test@1.59.1
```

No new Python dependency is required for Phase 4 if targeted regressions reuse the existing pytest stack.

**Version verification:** Use `npm view @playwright/test version` during implementation. This research verified current versions against the official npm registry because sandboxed shell networking only allowed `curl`:

| Package | Verified Version | Published |
|---------|------------------|-----------|
| `@playwright/test` | `1.59.1` | 2026-04-01T17:59:00Z |
| `next` | `16.2.4` | 2026-04-15T22:33:47Z |
| `vitest` | `4.1.4` | 2026-04-09T07:36:52Z |
| `pytest` | `9.0.3` | 2026-04-07T17:16:16Z |

**Scope note:** Do not couple Phase 4 to a Next.js or Vitest upgrade. The repo currently works on Next 15.x and Vitest 2.x; adding Playwright and new CI jobs is sufficient.

## Architecture Patterns

### Recommended Project Structure

```text
.github/workflows/
├── ci.yml                               # Keep fast jobs; add required postgres + full-stack jobs
scripts/
├── smoke-compose.sh                     # Refactor to secure-default bootstrap + ops-token checks
tests/
├── test_run_isolation_overlap.py        # Existing overlap regression
├── test_worker_lease_heartbeat.py       # Existing heartbeat / ownership-loss regression
├── test_worker_job_lifecycle_postgres.py# Existing Postgres claim/reclaim regression
└── support/
    └── seed_fullstack_browser_fixture.py# New minimal run/artifact seeding helper
frontend/
├── playwright.config.ts                 # New Playwright config
├── tests/e2e/
│   ├── auth.setup.ts                    # Bootstrapped admin auth state
│   └── run-workflows.spec.ts            # Sign-in, run answer, deep dive, artifact flow
└── package.json                         # Add test:e2e script and Playwright dependency
```

### Pattern 1: Split CI by Truth Boundary

**What:** Keep the existing fast backend/frontend jobs, add one Postgres-only pytest job for concurrency regressions, and add one full-stack Compose job for secure-default integration plus browser coverage.

**When to use:** This repo already has fast local tests and a documented Compose stack; Phase 4 should add missing truth boundaries without replacing what is already useful.

**Example:**
```yaml
# Source: GitHub Actions PostgreSQL service-container docs + repo docker-compose workflow shape
jobs:
  backend:
    # existing SQLite-backed pytest job

  frontend:
    # existing lint + build job

  postgres-regressions:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_USER: edgar
          POSTGRES_PASSWORD: edgar
          POSTGRES_DB: edgar
        options: >-
          --health-cmd "pg_isready -U edgar -d edgar"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

  full-stack:
    runs-on: ubuntu-latest
    steps:
      - run: docker compose up -d --build
      - run: ./scripts/smoke-compose.sh
      - run: cd frontend && npx playwright test
```

### Pattern 2: Bootstrap Admin Once, Reuse Browser State

**What:** Authenticate one admin account in a Playwright setup project, save the cookie state under `playwright/.auth`, and reuse it in the real browser spec.

**When to use:** `QUAL-02` only needs a narrow read-mostly authenticated flow; the same admin account can be reused safely when tests run with one CI worker.

**Example:**
```typescript
// Source: Playwright auth docs + frontend login flow in frontend/src/components/auth/login-form.tsx
import path from "node:path";
import { expect, test as setup } from "@playwright/test";

const authFile = path.join(__dirname, "../playwright/.auth/admin.json");

setup("authenticate admin", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill(process.env.E2E_ADMIN_EMAIL!);
  await page.getByLabel("Password").fill(process.env.E2E_ADMIN_PASSWORD!);
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.waitForURL(/\/projects/);
  await expect(page).toHaveURL(/\/projects/);
  await page.context().storageState({ path: authFile });
});
```

Add `playwright/.auth` to `.gitignore`; the stored browser state contains usable auth material.

### Pattern 3: Seed a Deterministic Completed Run for Browser Tests

**What:** Create the admin/project/run/step/artifact fixture through the existing backend models and `ArtifactService`, executed inside the running `api` container so Postgres settings and artifact volumes match production-like paths.

**When to use:** The browser spec needs stable data for run answer, deep dive, and artifact delivery without invoking live SEC/LLM work.

**Example:**
```bash
# Source: repo patterns in tests/test_secure_defaults_api.py, tests/test_sprint3_transparency_api.py,
# and tests/test_artifact_content_delivery.py
docker compose exec -T api \
  python -m tests.support.seed_fullstack_browser_fixture
```

The seeding helper should:

- bootstrap the first admin through the real API or create an equivalent admin row once
- create a project and one completed run
- attach at least one run step, one artifact row, and one artifact blob
- return the project ID, run ID, artifact ID, and admin credentials to the browser step

### Pattern 4: Save Failure Diagnostics as Workflow Artifacts

**What:** Upload Playwright HTML reports, trace files, and Docker Compose logs whenever the browser/full-stack job fails.

**When to use:** Full-stack failures are otherwise expensive to reproduce locally.

**Example:**
```yaml
# Source: Playwright CI docs + GitHub workflow artifacts docs
- name: Save docker logs
  if: ${{ failure() }}
  run: mkdir -p .tmp/compose-logs && docker compose logs > .tmp/compose-logs/full-stack.log

- uses: actions/upload-artifact@v5
  if: ${{ !cancelled() }}
  with:
    name: full-stack-diagnostics
    path: |
      frontend/playwright-report/
      frontend/test-results/
      .tmp/compose-logs/
```

### Anti-Patterns to Avoid

- **Reopening registration or removing ops auth in CI:** This would make the new gate lie about the secure-default deployment path.
- **Driving live SEC or optional LLM execution from the browser test:** It creates flaky, slow failures outside the scope of `QUAL-02`.
- **Replacing all current CI with one giant Compose job:** It reduces failure isolation and violates `D-02`.
- **Testing run answer / deep dive as a non-admin user:** The current pages request admin-gated payload expansions and will fail for the wrong reason.
- **Adding production-only test endpoints just for seeding:** Reuse existing service/model seams instead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Browser automation for authenticated SSR flows | Custom curl plus HTML scraping scripts | `@playwright/test` with setup auth state | Playwright already gives browser contexts, retries, traces, and CI-friendly diagnostics |
| Postgres lifecycle for targeted CI tests | Bespoke shell scripts that start/stop local Postgres | GitHub Actions PostgreSQL service containers | Official pattern, easy localhost wiring, and fast startup for repo pytest slices |
| Failure report bundling | Ad-hoc tar/zip logic | GitHub workflow artifacts + Playwright report/traces + Compose logs | Standard artifact flow is already supported by Actions and easier to inspect |
| Full-stack runtime emulation | A separate CI-only stack definition | The checked-in `docker-compose.yml` and refactored smoke script | Keeps CI aligned with the documented product contract |

**Key insight:** Phase 4 should add truthful orchestration and diagnostics around existing seams, not invent a parallel testing platform.

## Common Pitfalls

### Pitfall 1: CI Still Uses Insecure Smoke Assumptions

**What goes wrong:** The full-stack gate passes only because registration is left open or ops routes are hit without the required token.

**Why it happens:** The current `scripts/smoke-compose.sh` still creates a user through `POST /v1/auth/register` and calls `/v1/worker/health` without an ops bearer token.

**How to avoid:** Refactor the smoke path to bootstrap the first admin explicitly, log in through the real secure flow, and send `Authorization: Bearer $EDGAR_BACKEND_OPS_API_TOKEN` to `/metrics` and `/v1/worker/health`.

**Warning signs:** The smoke step succeeds with no bootstrap token configured, or unauthenticated calls to `/metrics` return `200`.

### Pitfall 2: Browser Tests Use the Wrong Account Type

**What goes wrong:** Run answer or deep-dive pages fail with a `403` or unexpected error even though login itself succeeds.

**Why it happens:** `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx` and `/trace/page.tsx` request `include_payloads=true`, and `backend/api/routes/runs.py` guards that behind `require_admin_debug_access(...)`.

**How to avoid:** Use a bootstrapped admin account for the browser setup step and reuse that stored state across the test.

**Warning signs:** `/login` succeeds, but the first run page request fails while simple project pages still work.

### Pitfall 3: Browser Tests Execute a Real Analysis Run

**What goes wrong:** CI becomes slow and flaky because the browser step now depends on live SEC, filesystem timing, worker timing, or optional LLM configuration.

**Why it happens:** It is tempting to verify the UI by creating a run and clicking Execute instead of seeding a finished run.

**How to avoid:** Seed a minimal completed run/step/artifact fixture directly in Postgres and artifact storage, then test only the authenticated read path.

**Warning signs:** Browser jobs wait on worker completion, hit external networks, or time out intermittently on run creation/execution.

### Pitfall 4: Concurrency Regressions Are Buried in the Full-Stack Job

**What goes wrong:** Lease or collision failures show up only in the slow Compose gate, making diagnosis noisy and reruns expensive.

**Why it happens:** Existing overlap/heartbeat/Postgres tests already exist, but CI does not isolate them as a required slice.

**How to avoid:** Add a dedicated Postgres pytest job for `tests/test_run_isolation_overlap.py`, `tests/test_worker_lease_heartbeat.py`, and `tests/test_worker_job_lifecycle_postgres.py`.

**Warning signs:** A lease bug requires combing through full-stack Docker logs instead of failing in a small pytest job.

### Pitfall 5: No Failure Artifacts

**What goes wrong:** Browser or Compose failures are not reproducible from the CI run itself.

**Why it happens:** Reports, traces, screenshots, and container logs are not uploaded.

**How to avoid:** Upload Playwright reports/traces and Docker logs on every failure path.

**Warning signs:** Engineers need to rerun the workflow locally to learn which screen or network request failed.

## Code Examples

Verified patterns from official sources and the current repo:

### Playwright Config for This Repo

```typescript
// Source: https://playwright.dev/docs/ci
// Source: https://playwright.dev/docs/trace-viewer-intro
import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["html", { open: "never" }], ["list"]] : "list",
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
    trace: "on-first-retry",
  },
});
```

### Targeted Postgres Regression Job

```yaml
# Source: https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers
# Source: repo tests/postgres_queue_test_utils.py
postgres-regressions:
  runs-on: ubuntu-latest
  services:
    postgres:
      image: postgres:16
      env:
        POSTGRES_USER: edgar
        POSTGRES_PASSWORD: edgar
        POSTGRES_DB: edgar
      options: >-
        --health-cmd "pg_isready -U edgar -d edgar"
        --health-interval 10s
        --health-timeout 5s
        --health-retries 5
      ports:
        - 5432:5432
  steps:
    - uses: actions/checkout@v5
    - uses: actions/setup-python@v5
      with:
        python-version: "3.12"
    - name: Install dependencies
      run: pip install --upgrade pip && pip install -r requirements-dev.txt
    - name: Run targeted regressions
      env:
        PYTHONPATH: ${{ github.workspace }}
        EDGAR_TEST_POSTGRES_URL: postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar
      run: >
        python -m pytest
        tests/test_run_isolation_overlap.py
        tests/test_worker_lease_heartbeat.py
        tests/test_worker_job_lifecycle_postgres.py
        -q --tb=short
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| PR CI = SQLite backend pytest + frontend lint/build only | Keep fast jobs, then add a required Postgres regression slice and a required full-stack Compose gate | Current project need as of 2026-04-16 | Pull requests fail on the same stack shape operators actually run |
| Manual or per-test browser login | One setup auth project with stored browser state | Current Playwright auth guidance | Faster and less flaky authenticated browser coverage |
| Browser failures debugged from raw logs only | HTML report + trace files + uploaded artifacts | Current Playwright CI + trace guidance | Failures become inspectable without reproducing locally |
| Optional compose smoke that predates secure defaults | Secure-default smoke with bootstrap admin and ops token | Required after Phase 3 decisions | CI validates real auth posture instead of bypassing it |

**Deprecated/outdated:**

- `.github/workflows/compose-smoke.yml` in its current form is outdated for this phase because it only starts `db + migrate + api`, does not gate PRs, and predates the secure-default auth contract.
- Relying on Vitest/lint/build alone for frontend verification is outdated for `QUAL-02`; it misses cookie-backed auth, run-page SSR fetches, and artifact proxy delivery.

## Open Questions

1. **Where should the full-stack browser fixture seeding helper live?**
   - What we know: It should reuse existing backend models/services and run inside the Compose stack so artifact paths land on the mounted volume.
   - What's unclear: Whether this repo will prefer `tests/support/` or `scripts/ci/` for a one-off seeding module.
   - Recommendation: Put it under `tests/support/` if it is purely test support; keep it importable from `docker compose exec api python -m ...`.

2. **Should the full-stack gate stay in `.github/workflows/ci.yml` or move behind a reusable workflow?**
   - What we know: The phase allows either, but the gate must be PR-required and easy to target from branch protection.
   - What's unclear: Repo preference for one larger workflow file versus a small calling workflow plus a reusable one.
   - Recommendation: Keep it in `ci.yml` unless the file becomes materially harder to maintain; explicit named jobs are simplest for branch protection.

3. **How much run data does the browser fixture need to seed?**
   - What we know: The browser flow needs at least one project, one completed run, enough step data for deep dive, and at least one artifact blob for proxy delivery.
   - What's unclear: The exact minimum transparency/model-call payload required to keep the current trace UI happy without over-seeding.
   - Recommendation: Start from the minimal shapes already used in `tests/test_sprint3_transparency_api.py` and `tests/test_artifact_content_delivery.py`, then add only fields the page actually dereferences.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend pytest jobs and local helper scripts | Partial | `3.11.0` | CI already uses `actions/setup-python` for `3.12`; Docker backend image also provides Python 3.12 |
| Node.js | Frontend install/build and Playwright runner | Yes | `v24.9.0` | - |
| npm | Frontend dependency install | Yes | `11.6.0` | - |
| Docker Engine | Full-stack Compose gate | Yes | `29.3.1` | - |
| Docker Compose | Documented stack gate | Yes | `v5.1.1` | - |
| Playwright repo dependency | Browser tests | No | - | Add `@playwright/test` and run `npx playwright install --with-deps chromium` |

**Missing dependencies with no fallback:**

- None for CI planning. GitHub Actions can supply Python 3.12, and Docker is available locally.

**Missing dependencies with fallback:**

- Local Python 3.12 is not installed; use the existing Docker image or CI `setup-python` for parity.
- Repo-local Playwright is not installed yet; Phase 4 should add it as a frontend dev dependency.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | `pytest` + `Vitest` + `Playwright` |
| Config file | `pytest.ini`, `frontend/vitest.config.ts`, `frontend/playwright.config.ts` (new in this phase) |
| Quick run command | `python -m pytest tests/test_run_isolation_overlap.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle_postgres.py -q --tb=short` |
| Full suite command | `python -m pytest tests/ -q --tb=short && (cd frontend && npm run test && npm run build) && docker compose up -d --build && ./scripts/smoke-compose.sh && (cd frontend && npx playwright test)` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | PR CI validates the documented Postgres + API + worker + frontend path | full-stack integration | `docker compose up -d --build && ./scripts/smoke-compose.sh` | ❌ Wave 0 |
| QUAL-02 | Authenticated sign-in, run answer, deep dive, and artifact delivery stay working | browser/e2e | `cd frontend && npx playwright test tests/e2e/run-workflows.spec.ts` | ❌ Wave 0 |
| QUAL-03 | Collision, lease-expiry, and Postgres queue regressions stay covered | targeted pytest integration | `EDGAR_TEST_POSTGRES_URL=postgresql+psycopg2://edgar:edgar@127.0.0.1:5432/edgar python -m pytest tests/test_run_isolation_overlap.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle_postgres.py -q --tb=short` | ✅ tests exist; ❌ CI slice |

### Sampling Rate

- **Per task commit:** Run the requirement-specific command from the table above.
- **Per wave merge:** `python -m pytest tests/ -q --tb=short && (cd frontend && npm run test && npm run build)`
- **Phase gate:** Full suite green plus required `postgres-regressions` and `full-stack` CI jobs before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `frontend/playwright.config.ts` - Playwright config, retries, reporters, and base URL
- [ ] `frontend/tests/e2e/auth.setup.ts` - bootstrap-admin login and stored auth state
- [ ] `frontend/tests/e2e/run-workflows.spec.ts` - narrow authenticated flow for sign-in, run answer, deep dive, and artifact delivery
- [ ] `tests/support/seed_fullstack_browser_fixture.py` - deterministic completed-run fixture seeding inside the running stack
- [ ] `.github/workflows/ci.yml` - add required `postgres-regressions` and `full-stack` jobs
- [ ] `scripts/smoke-compose.sh` - secure-default bootstrap/admin and ops-token verification instead of open registration assumptions
- [ ] Framework install: `cd frontend && npm install -D @playwright/test@1.59.1 && npx playwright install --with-deps chromium`

## Sources

### Primary (HIGH confidence)

- Repository inspection: `.github/workflows/ci.yml`, `.github/workflows/compose-smoke.yml`, `scripts/smoke-compose.sh`, `docker-compose.yml`, `docs/local-stack.md`, `docs/auth-api.md`, `tests/test_secure_defaults_api.py`, `tests/test_artifact_content_delivery.py`, `tests/test_worker_lease_heartbeat.py`, `tests/test_worker_job_lifecycle_postgres.py`, `tests/test_run_isolation_overlap.py`, `tests/test_sprint3_transparency_api.py`, `frontend/src/actions/auth.ts`, `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`, `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`
- https://playwright.dev/docs/ci - CI install steps, workers recommendation, GitHub Actions pattern, artifact upload example
- https://playwright.dev/docs/auth - setup-project authentication and stored browser state guidance
- https://playwright.dev/docs/trace-viewer-intro - retry and trace defaults for CI debugging
- https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers - official service-container pattern for Postgres-backed jobs
- https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/control-workflow-concurrency - workflow/job concurrency behavior
- https://docs.github.com/en/actions/concepts/workflows-and-actions/workflow-artifacts - standard artifact persistence model for workflow outputs
- https://registry.npmjs.org/%40playwright%2Ftest/latest - verified current `@playwright/test` version
- https://registry.npmjs.org/next/latest - verified current Next.js version for ecosystem currency
- https://registry.npmjs.org/vitest/latest - verified current Vitest version for ecosystem currency
- https://pypi.org/pypi/pytest/json - verified current pytest version

### Secondary (MEDIUM confidence)

- None

### Tertiary (LOW confidence)

- None

## Metadata

**Confidence breakdown:**

- Standard stack: HIGH - recommended tools are either already in the repo or directly supported by official Playwright/GitHub docs and official package registries
- Architecture: HIGH - job split, auth posture, and seeding strategy are grounded in current repo seams plus official CI/browser patterns
- Pitfalls: HIGH - main risks are visible directly in current scripts/pages/tests and confirmed by prior phase constraints

**Research date:** 2026-04-16
**Valid until:** 2026-04-23
