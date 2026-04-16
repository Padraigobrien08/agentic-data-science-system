---
phase: 04-ci-coverage
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - scripts/smoke-compose.sh
  - .github/workflows/compose-smoke.yml
autonomous: true
requirements:
  - QUAL-01
must_haves:
  truths:
    - "A pull request can boot the documented `db + migrate + api + worker + web` stack, not just API-only Compose or SQLite-backed pytest."
    - "The smoke gate validates the secure-default bootstrap-admin and ops-token path instead of assuming open registration or public ops routes."
    - "Full-stack workflow failures preserve enough diagnostics to debug container and smoke failures without rerunning blind."
  artifacts:
    - path: scripts/smoke-compose.sh
      provides: "Secure-default full-stack smoke contract for bootstrap auth, ops routes, and web availability"
    - path: .github/workflows/compose-smoke.yml
      provides: "Required PR workflow for the documented multi-service Compose stack"
  key_links:
    - from: .github/workflows/compose-smoke.yml
      to: scripts/smoke-compose.sh
      via: "workflow invokes the smoke contract after booting the full stack"
      pattern: "docker compose up -d --build|./scripts/smoke-compose.sh"
    - from: scripts/smoke-compose.sh
      to: docs/auth-api.md
      via: "smoke uses the same bootstrap-admin and ops-token route semantics documented for operators"
      pattern: "/v1/auth/bootstrap|/metrics|/v1/worker/health"
    - from: scripts/smoke-compose.sh
      to: docker-compose.yml
      via: "smoke assumes the documented services and ports are present and healthy"
      pattern: "db|migrate|api|worker|web"
---

<objective>
Expand CI so pull requests boot and validate the documented multi-service stack under the secure-default auth posture.

Purpose: satisfy the Phase 4 stack-truth boundary before browser coverage is layered on top, so CI proves the real `db + migrate + api + worker + web` contract rather than the older API-only smoke path.
Output: a secure-default smoke script and a PR-triggered Compose workflow that boots the full stack, validates bootstrap and ops auth, and preserves diagnostics on failure.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/04-ci-coverage/04-CONTEXT.md
@.planning/phases/04-ci-coverage/04-RESEARCH.md
@.planning/phases/04-ci-coverage/04-VALIDATION.md
@scripts/smoke-compose.sh
@.github/workflows/compose-smoke.yml
@docker-compose.yml
@docs/local-stack.md
@docs/auth-api.md

<interfaces>
From `scripts/smoke-compose.sh`:
```bash
API_BASE="${API_BASE:-http://127.0.0.1:${API_PORT}}"
WEB_BASE="${WEB_BASE:-http://127.0.0.1:${WEB_PORT}}"
```

From `.github/workflows/compose-smoke.yml`:
```yaml
on:
  workflow_dispatch:
```

From `docs/auth-api.md`:
```text
POST /v1/auth/bootstrap
GET /metrics
GET /v1/worker/health
```
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: Replace insecure smoke assumptions with the secure-default full-stack contract</name>
  <files>scripts/smoke-compose.sh</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
scripts/smoke-compose.sh
docker-compose.yml
docs/local-stack.md
docs/auth-api.md
tests/test_secure_defaults_api.py</read_first>
  <behavior>
    - The smoke path boots against the documented full stack and no longer depends on self-service registration.
    - The smoke path uses deterministic admin credentials with `POST /v1/auth/bootstrap` plus `POST /v1/auth/login` so reruns remain valid after bootstrap returns `409`.
    - The smoke path sends `Authorization: Bearer $EDGAR_BACKEND_OPS_API_TOKEN` to `/metrics` and `/v1/worker/health`.
    - The smoke path verifies `db`, `migrate`, `api`, `worker`, and `web` availability without executing a live EDGAR run.
  </behavior>
  <action>Rewrite `scripts/smoke-compose.sh` so it validates the full documented stack instead of the old API-only or open-registration path. Keep the existing `pg_isready`, Alembic, API health, worker-container-running, and web checks, but remove the `POST /v1/auth/register` flow and the live `POST /v1/runs` execution loop. Add exact environment requirements for `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`, `EDGAR_BACKEND_OPS_API_TOKEN`, `EDGAR_SMOKE_ADMIN_EMAIL`, and `EDGAR_SMOKE_ADMIN_PASSWORD`, failing early with a clear `smoke:` message if any are missing. Use `EDGAR_SMOKE_ADMIN_EMAIL` and `EDGAR_SMOKE_ADMIN_PASSWORD` in the bootstrap JSON payload, treat `409 Bootstrap already completed` as acceptable, and always follow bootstrap with `POST /v1/auth/login` using those same fixed credentials so reruns can still obtain a bearer token for one authenticated protected request such as `GET /v1/projects`. Call `GET /metrics` and `GET /v1/worker/health` with `Authorization: Bearer $EDGAR_BACKEND_OPS_API_TOKEN` and fail if either returns non-200. Keep the script host-driven and deterministic: do not queue or execute a live analysis run, and do not rely on external SEC or LLM behavior.</action>
  <acceptance_criteria>`scripts/smoke-compose.sh` contains `/v1/auth/bootstrap`.
`scripts/smoke-compose.sh` contains `/v1/auth/login`.
`scripts/smoke-compose.sh` contains `EDGAR_SMOKE_ADMIN_EMAIL`.
`scripts/smoke-compose.sh` contains `EDGAR_SMOKE_ADMIN_PASSWORD`.
`scripts/smoke-compose.sh` contains `/metrics` and sends an `Authorization: Bearer` header for the ops token.
`scripts/smoke-compose.sh` contains `/v1/worker/health` and sends an `Authorization: Bearer` header for the ops token.
`scripts/smoke-compose.sh` no longer contains `/v1/auth/register`.
`scripts/smoke-compose.sh` no longer contains `enqueue_execution`.
`scripts/smoke-compose.sh` still checks `db`, `api`, `worker`, and `web`.
Running `docker compose up -d --build && ./scripts/smoke-compose.sh` exits 0 with the secure-default env vars set.</acceptance_criteria>
  <verify>
    <automated>docker compose up -d --build && ./scripts/smoke-compose.sh</automated>
  </verify>
  <done>The smoke contract now validates the real secure-default stack shape instead of relying on pre-Phase-3 assumptions or live run execution.</done>
</task>

<task type="auto">
  <name>Task 2: Promote the full-stack smoke into a required PR workflow with diagnostics</name>
  <files>.github/workflows/compose-smoke.yml</files>
  <read_first>.planning/phases/04-ci-coverage/04-CONTEXT.md
.planning/phases/04-ci-coverage/04-RESEARCH.md
.planning/phases/04-ci-coverage/04-VALIDATION.md
.github/workflows/compose-smoke.yml
scripts/smoke-compose.sh
docker-compose.yml
.github/workflows/ci.yml</read_first>
  <behavior>
    - The former optional Compose smoke runs automatically on pull requests.
    - The workflow boots the full stack, not just `api`.
    - The workflow injects explicit secure-default CI secrets for JWT, bootstrap, and ops tokens.
    - The workflow uploads Compose logs on failure and tears the stack down reliably.
  </behavior>
  <action>Refactor `.github/workflows/compose-smoke.yml` from an optional API-only smoke into a PR-triggered required full-stack workflow. Change the workflow name to `Full Stack` and the job name to `full-stack`. Add `pull_request` to the triggers while keeping manual dispatch if useful. Replace `docker compose up -d --build api` with `docker compose up -d --build` so `db`, `migrate`, `api`, `worker`, and `web` all start. Set explicit workflow env values for `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`, `EDGAR_BACKEND_OPS_API_TOKEN`, `EDGAR_SMOKE_ADMIN_EMAIL`, and `EDGAR_SMOKE_ADMIN_PASSWORD` so the stack satisfies the secure-default startup contract and the smoke login path is deterministic across reruns. Replace the ad-hoc curl wait loop with `./scripts/smoke-compose.sh`. Add a failure-path step that writes `docker compose logs` to a diagnostics directory and uploads it with `actions/upload-artifact@v4` or later. Keep the teardown step as `docker compose down -v` under `if: always()` so the workflow cleans up even after smoke failure.</action>
  <acceptance_criteria>`.github/workflows/compose-smoke.yml` contains `pull_request:`.
`.github/workflows/compose-smoke.yml` contains `name: Full Stack`.
`.github/workflows/compose-smoke.yml` contains `docker compose up -d --build`.
`.github/workflows/compose-smoke.yml` contains `./scripts/smoke-compose.sh`.
`.github/workflows/compose-smoke.yml` sets `EDGAR_BACKEND_JWT_SECRET`.
`.github/workflows/compose-smoke.yml` sets `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`.
`.github/workflows/compose-smoke.yml` sets `EDGAR_BACKEND_OPS_API_TOKEN`.
`.github/workflows/compose-smoke.yml` sets `EDGAR_SMOKE_ADMIN_EMAIL`.
`.github/workflows/compose-smoke.yml` sets `EDGAR_SMOKE_ADMIN_PASSWORD`.
`.github/workflows/compose-smoke.yml` uploads Compose diagnostics on failure.
`.github/workflows/compose-smoke.yml` contains `docker compose down -v` under an always-run cleanup step.</acceptance_criteria>
  <verify>
    <automated>docker compose up -d --build && ./scripts/smoke-compose.sh</automated>
  </verify>
  <done>Pull requests now have a dedicated required workflow that exercises the documented full stack under the secure-default contract and preserves useful diagnostics when it fails.</done>
</task>

</tasks>

<verification>
Run the secure-default smoke command after each task so the script and workflow stay aligned around the same stack contract before browser coverage is added later.
</verification>

<success_criteria>
Phase 4 becomes execution-ready for frontend/browser layering when pull requests can boot the documented multi-service stack, pass secure-default bootstrap and ops checks, and surface actionable diagnostics on failure.
</success_criteria>

<output>
After completion, create `.planning/phases/04-ci-coverage/04-ci-coverage-01-SUMMARY.md`
</output>
