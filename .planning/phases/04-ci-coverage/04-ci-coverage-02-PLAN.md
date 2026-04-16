---
phase: 04-ci-coverage
plan: 02
type: execute
wave: 2
depends_on:
  - 04-01
files_modified:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/.gitignore
  - frontend/playwright.config.ts
  - frontend/tests/e2e/fixture.ts
  - frontend/tests/e2e/auth.setup.ts
  - frontend/tests/e2e/run-workflows.spec.ts
  - tests/support/seed_fullstack_browser_fixture.py
  - .github/workflows/compose-smoke.yml
autonomous: true
requirements:
  - QUAL-01
  - QUAL-02
must_haves:
  truths:
    - "Browser coverage runs against the live Compose web stack with a bootstrapped admin account rather than mocked or unit-only flows."
    - "The Playwright path uses deterministic seeded run data instead of triggering a live EDGAR analysis in CI."
    - "The full-stack workflow publishes Playwright artifacts so browser regressions are diagnosable."
  artifacts:
    - path: frontend/playwright.config.ts
      provides: "Playwright CI/browser harness for the frontend app"
    - path: frontend/tests/e2e/run-workflows.spec.ts
      provides: "Authenticated browser regression for run answer, deep dive, and artifact delivery"
    - path: tests/support/seed_fullstack_browser_fixture.py
      provides: "Deterministic seeded admin/project/run/artifact fixture for browser CI"
  key_links:
    - from: frontend/tests/e2e/auth.setup.ts
      to: frontend/src/app/login/page.tsx
      via: "setup authenticates through the real login page and cookie-backed session path"
      pattern: "/login|Sign in"
    - from: frontend/tests/e2e/run-workflows.spec.ts
      to: frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
      via: "browser spec validates the real run-answer and deep-dive pages"
      pattern: "Run answer|Deep dive"
    - from: tests/support/seed_fullstack_browser_fixture.py
      to: .github/workflows/compose-smoke.yml
      via: "workflow seeds deterministic data before Playwright runs"
      pattern: "seed_fullstack_browser_fixture|E2E_FIXTURE_PATH"
---

<objective>
Add narrow browser-level verification for authenticated run workflows on top of the secure-default full-stack gate.

Purpose: satisfy QUAL-02 by covering sign-in, run answer, deep-dive navigation, and artifact proxy delivery through the real Next.js app without turning CI into a live-analysis workflow.
Output: Playwright harness and deterministic seed data wired into the full-stack workflow.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/phases/04-ci-coverage/04-CONTEXT.md
@.planning/phases/04-ci-coverage/04-RESEARCH.md
@.planning/phases/04-ci-coverage/04-VALIDATION.md
@.planning/phases/04-ci-coverage/04-ci-coverage-01-PLAN.md
@frontend/package.json
@frontend/.gitignore
@frontend/src/actions/auth.ts
@frontend/src/app/login/page.tsx
@frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
@frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
@frontend/src/app/api/artifacts/[artifactId]/content/route.ts
@frontend/src/lib/auth/backend-auth.ts
@tests/test_secure_defaults_api.py
@tests/test_artifact_content_delivery.py
@.github/workflows/compose-smoke.yml

<interfaces>
From `frontend/src/actions/auth.ts`:
```ts
export async function loginAction(_prev: LoginState, formData: FormData): Promise<LoginState>
```

From `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`:
```ts
export async function GET(req: Request, context: { params: Promise<{ artifactId: string }> })
```

From `frontend/package.json`:
```json
{
  "scripts": {
    "test": "vitest run"
  }
}
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add Playwright config, auth setup, and the narrow browser regression spec</name>
  <files>frontend/package.json, frontend/package-lock.json, frontend/.gitignore, frontend/playwright.config.ts, frontend/tests/e2e/fixture.ts, frontend/tests/e2e/auth.setup.ts, frontend/tests/e2e/run-workflows.spec.ts</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
frontend/package.json
frontend/.gitignore
frontend/src/actions/auth.ts
frontend/src/app/login/page.tsx
frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx
frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
frontend/src/app/api/artifacts/[artifactId]/content/route.ts
frontend/src/lib/auth/backend-auth.ts</read_first>
  <behavior>
    - The frontend has a dedicated `test:e2e` command backed by Playwright.
    - Playwright stores authenticated admin state in an ignored path and reuses it for the real browser spec.
    - The browser spec reads deterministic fixture data from `E2E_FIXTURE_PATH`.
    - The browser spec validates sign-in, run answer, deep-dive navigation, and artifact-content delivery.
  </behavior>
  <action>Update `frontend/package.json` and `frontend/package-lock.json` to add `@playwright/test@1.59.1` as a dev dependency and add the exact script `"test:e2e": "playwright test"`. Update `frontend/.gitignore` to ignore `playwright/.auth/`, `playwright-report/`, and `test-results/`. Create `frontend/playwright.config.ts` with `testDir: "./tests/e2e"`, `use.baseURL` sourced from `PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000"`, `retries: process.env.CI ? 2 : 0`, HTML + list reporters, trace/screenshot retention on failure, and two projects: `setup` running `tests/e2e/auth.setup.ts`, then `chromium` depending on `setup` and using `storageState: "playwright/.auth/admin.json"`. Create `frontend/tests/e2e/fixture.ts` that reads and parses JSON from the exact env var `E2E_FIXTURE_PATH` and returns `admin_email`, `admin_password`, `project_id`, `run_id`, and `artifact_id`. Create `frontend/tests/e2e/auth.setup.ts` so it loads the fixture, visits `/login`, fills the real email/password form, waits for a `/projects` URL, and writes the authenticated state to `playwright/.auth/admin.json`. Create `frontend/tests/e2e/run-workflows.spec.ts` so it loads the same fixture, visits `/projects/${project_id}/runs/${run_id}`, asserts visible `Run answer`, clicks or loads the `Deep dive` route at `/projects/${project_id}/runs/${run_id}/trace`, and uses Playwright request or page navigation against `/api/artifacts/${artifact_id}/content?disposition=inline` to assert `200` plus known seeded content text. Do not trigger live run execution anywhere in the spec.</action>
  <acceptance_criteria>`frontend/package.json` contains `"test:e2e": "playwright test"`.
`frontend/package.json` contains `@playwright/test`.
`frontend/.gitignore` contains `playwright/.auth/`.
`frontend/.gitignore` contains `playwright-report/`.
`frontend/.gitignore` contains `test-results/`.
`frontend/playwright.config.ts` exists and defines a `setup` project plus a `chromium` project that uses `playwright/.auth/admin.json`.
`frontend/tests/e2e/fixture.ts` reads `E2E_FIXTURE_PATH`.
`frontend/tests/e2e/auth.setup.ts` visits `/login` and writes `playwright/.auth/admin.json`.
`frontend/tests/e2e/run-workflows.spec.ts` contains `Run answer`, `Deep dive`, and `/api/artifacts/`.
`cd frontend && npm run test:e2e -- --list` exits 0.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test:e2e -- --list</automated>
  </verify>
  <done>The repo has a deterministic Playwright harness ready to run against a live stack once fixture seeding and workflow integration are added.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Seed deterministic browser data and run Playwright inside the full-stack workflow</name>
  <files>tests/support/seed_fullstack_browser_fixture.py, .github/workflows/compose-smoke.yml</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
.planning/phases/04-ci-coverage/04-ci-coverage-01-PLAN.md
.github/workflows/compose-smoke.yml
tests/test_secure_defaults_api.py
tests/test_artifact_content_delivery.py
backend/services/artifact_service.py
backend/db/session.py
backend/models/analysis_run.py
backend/models/run_step.py
backend/models/artifact.py</read_first>
  <behavior>
    - The full-stack workflow seeds deterministic admin/project/run/artifact data before browser execution.
    - The seeding helper prints a JSON fixture file with exact keys for the Playwright harness.
    - The workflow installs Playwright browsers, exports `PLAYWRIGHT_BASE_URL` and `E2E_FIXTURE_PATH`, and runs the narrow browser spec after smoke passes.
    - Playwright reports, test results, fixture JSON, and Compose logs are uploaded on failure.
  </behavior>
  <action>Create `tests/support/seed_fullstack_browser_fixture.py` as a Python module runnable with `python -m tests.support.seed_fullstack_browser_fixture`. Inside the running API container, it must use the configured database/artifact services to create or upsert one admin user with a stable email/password, one project, one completed run, at least one run step, and one persisted artifact whose content includes a deterministic marker string such as `Seeded artifact content for CI browser test.`. The script must print JSON to stdout with the exact keys `admin_email`, `admin_password`, `project_id`, `run_id`, and `artifact_id`. Then extend `.github/workflows/compose-smoke.yml` so, after `./scripts/smoke-compose.sh` passes, it runs `docker compose exec -T api python -m tests.support.seed_fullstack_browser_fixture > .tmp/e2e-fixture.json`, uses `actions/setup-node@v4` with `node-version: "20"` and npm cache against `frontend/package-lock.json`, installs frontend deps with `npm ci`, installs Chromium with `npx playwright install --with-deps chromium`, sets `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000` and `E2E_FIXTURE_PATH=${{ github.workspace }}/.tmp/e2e-fixture.json`, and runs `npm run test:e2e` from `frontend/`. Add artifact upload steps for `frontend/playwright-report/`, `frontend/test-results/`, `.tmp/e2e-fixture.json`, and Compose logs under failure or non-cancelled conditions so browser regressions are diagnosable.</action>
  <acceptance_criteria>`tests/support/seed_fullstack_browser_fixture.py` exists.
`tests/support/seed_fullstack_browser_fixture.py` prints JSON keys `admin_email`, `admin_password`, `project_id`, `run_id`, and `artifact_id`.
`tests/support/seed_fullstack_browser_fixture.py` writes an artifact whose content includes `Seeded artifact content for CI browser test.`.
`.github/workflows/compose-smoke.yml` runs `python -m tests.support.seed_fullstack_browser_fixture`.
`.github/workflows/compose-smoke.yml` uses `actions/setup-node@v4`.
`.github/workflows/compose-smoke.yml` sets Node version `20`.
`.github/workflows/compose-smoke.yml` sets `PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000`.
`.github/workflows/compose-smoke.yml` sets `E2E_FIXTURE_PATH=${{ github.workspace }}/.tmp/e2e-fixture.json`.
`.github/workflows/compose-smoke.yml` runs `npx playwright install --with-deps chromium`.
`.github/workflows/compose-smoke.yml` runs `npm run test:e2e`.
`.github/workflows/compose-smoke.yml` uploads `frontend/playwright-report/` and `frontend/test-results/`.</acceptance_criteria>
  <verify>
    <automated>python3 -m py_compile tests/support/seed_fullstack_browser_fixture.py && (cd frontend && npm run test:e2e -- --list)</automated>
  </verify>
  <done>The full-stack workflow now exercises the real authenticated browser path against deterministic seeded data without relying on live EDGAR execution.</done>
</task>

</tasks>

<verification>
Validate the Playwright harness parsing before workflow wiring, then rerun the same parse check after fixture and workflow integration so the browser path remains deterministic and executable.
</verification>

<success_criteria>
Phase 4 will satisfy QUAL-02 when pull requests can seed deterministic admin/run data, authenticate through the real login flow, open run answer and deep-dive pages, and fetch artifact content through the app proxy inside the live Compose stack.
</success_criteria>

<output>
After completion, create `.planning/phases/04-ci-coverage/04-ci-coverage-02-SUMMARY.md`
</output>
