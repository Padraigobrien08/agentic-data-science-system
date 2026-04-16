# Phase 4: CI Coverage - Context

**Gathered:** 2026-04-16
**Status:** Ready for planning

<domain>
## Phase Boundary

Align automated verification with the documented product stack and the highest-risk user journeys. This phase covers PR-required CI for the documented Postgres + API + worker + web stack, secure-default auth setup inside CI, authenticated frontend coverage for login/run answer/trace/artifact delivery, and merge-gated concurrency or lease regressions.

It does not include live SEC validation, storage-retention policy, or broader observability work beyond what is needed to make CI truthful about the current product.

</domain>

<decisions>
## Implementation Decisions

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

### the agent's Discretion
- Exact workflow/job split, names, and whether the full-stack gate lives in `ci.yml` or a referenced workflow, as long as it is PR-required
- Exact CI env/secret injection mechanics for bootstrap and ops credentials
- Exact browser-test wiring, fixtures, and narrow path coverage, as long as the test remains focused on authenticated run workflows and artifact delivery
- Exact targeted regression subset promoted into required slices, as long as it covers the collision, lease, and Postgres queue risks called out by `QUAL-03`

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — hardening intent, brownfield constraints, and why CI depth is the next trust boundary
- `.planning/REQUIREMENTS.md` — `QUAL-01`, `QUAL-02`, and `QUAL-03` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 4 goal, planned breakdown, and success criteria
- `.planning/STATE.md` — current project position after Phase 3 completion

### Prior phase decisions that constrain this phase
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — normal execution now depends on explicit run-scoped workspaces and collision regressions should stay covered
- `.planning/phases/02-worker-resilience/02-CONTEXT.md` — lease renewal, stale-lease recovery, and operator-truthfulness expectations that CI must keep gated
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — secure-default auth, bootstrap flow, and ops-token protection that CI must validate instead of bypassing

### Existing stack, risk, and test context
- `.planning/codebase/CONCERNS.md` — documents the CI, frontend, and concurrency gaps this phase must close
- `.planning/codebase/TESTING.md` — current backend/frontend testing patterns and the lack of browser E2E coverage
- `docs/local-stack.md` — documented stack and smoke expectations for Postgres, API, worker, frontend, bootstrap, and ops auth
- `docs/auth-api.md` — secure auth posture, bootstrap admin, JWT flow, and ops-token routes
- `docker-compose.yml` — the documented service topology this phase should gate in CI
- `.github/workflows/ci.yml` and `.github/workflows/compose-smoke.yml` — current CI posture and the existing non-gating compose smoke

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `.github/workflows/ci.yml` — already provides the fast backend/frontend baseline that should remain in place beside any heavier integration gate
- `.github/workflows/compose-smoke.yml` and `scripts/smoke-compose.sh` — existing stack-smoke assets that can be upgraded into truthful secure-default verification instead of starting from zero
- `tests/test_worker_job_lifecycle_postgres.py`, `tests/test_worker_lease_heartbeat.py`, and `tests/test_run_isolation_overlap.py` — focused regressions already cover much of the collision/lease risk that needs promotion into PR-required slices
- `tests/test_secure_defaults_api.py` and `tests/test_artifact_content_delivery.py` — existing API-level regressions already exercise ops auth, bootstrap posture, and artifact delivery semantics
- `frontend/src/actions/auth.ts`, `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`, and the run/trace pages under `frontend/src/app/projects/[projectId]/runs/...` — stable web seams for authenticated flow and artifact-delivery coverage

### Established Patterns
- PR CI currently runs backend `pytest` on a SQLite-backed in-memory setup and frontend `lint + build`, but does not gate the documented Postgres + worker + web stack
- The optional compose smoke workflow only starts `db + migrate + api`, skips `worker` and `web`, and does not gate pull requests
- Secure defaults now require bootstrap-admin setup and an ops token, so the older smoke assumptions of open registration or public ops routes are no longer truthful
- Frontend tests today are unit/component Vitest suites; there is no Playwright/Cypress/browser-level coverage yet

### Integration Points
- `.github/workflows/ci.yml` — where PR-required job composition and gating decisions land
- `.github/workflows/compose-smoke.yml` and `scripts/smoke-compose.sh` — likely seams for stack verification refactor or promotion
- `docker-compose.yml` and `docs/local-stack.md` — the canonical runtime contract CI should mirror
- `frontend/src/actions/auth.ts`, `frontend/src/lib/auth/backend-auth.ts`, `frontend/src/lib/api/client.ts`, and `frontend/src/app/api/artifacts/[artifactId]/content/route.ts` — web auth/session/proxy seams for frontend integration coverage
- `tests/test_worker_job_lifecycle_postgres.py`, `tests/test_worker_lease_heartbeat.py`, `tests/test_run_isolation_overlap.py`, and related run-lifecycle tests — likely targeted regression slices for `QUAL-03`

</code_context>

<specifics>
## Specific Ideas

- User accepted the recommended defaults for all identified gray areas:
  - dedicated PR-required full-stack gate alongside existing fast jobs
  - secure-default bootstrap and ops-token auth in CI rather than relaxed test-only security
  - narrow browser-level coverage for authenticated frontend run workflows and artifact delivery
  - PR-required targeted concurrency and lease regressions instead of hiding them in slower/manual checks

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-ci-coverage*
*Context gathered: 2026-04-16*
