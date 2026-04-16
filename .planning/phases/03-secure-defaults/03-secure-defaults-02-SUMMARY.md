---
phase: 03-secure-defaults
plan: 02
subsystem: auth
tags: [fastapi, jwt, ops, metrics, artifacts, pytest]
requires:
  - phase: 02-worker-resilience
    provides: worker health and queue observability surfaces that now need secure-default protection
provides:
  - dedicated ops bearer auth for `/metrics` and `/v1/worker/health`
  - admin-only raw payload and artifact metadata expansions on owner-scoped routes
  - sanitized artifact provenance that avoids persisted absolute filesystem paths
affects: [03-secure-defaults-03, auth, ops, artifacts]
tech-stack:
  added: []
  patterns:
    - dedicated ops bearer dependency separate from end-user JWT auth
    - admin-gated debug expansions on summary-first owner routes
    - filename and run-workspace-relative artifact provenance instead of absolute source paths
key-files:
  created:
    - tests/test_secure_defaults_api.py
  modified:
    - backend/config/settings.py
    - backend/api/auth_deps.py
    - backend/api/routes/metrics.py
    - backend/api/routes/health.py
    - backend/api/routes/runs.py
    - backend/api/routes/artifacts.py
    - backend/services/artifact_service.py
    - tests/test_backend_health.py
    - tests/test_artifact_storage.py
    - tests/test_run_isolation_execution_service.py
key-decisions:
  - "Protected operational telemetry with a dedicated bearer token instead of reusing end-user JWTs."
  - "Kept run and artifact routes owner-scoped but required admin privilege before honoring raw expansion flags."
  - "Replaced persisted artifact source_path values with source_filename and run-workspace-relative provenance."
patterns-established:
  - "Ops-only routes depend on auth_deps.require_ops_token and always return WWW-Authenticate: Bearer on missing or invalid credentials."
  - "Raw payload access remains opt-in through existing query flags, but only admin-owned sessions can activate those larger views."
requirements-completed: [SECU-03]
duration: 7min
completed: 2026-04-16
---

# Phase 03 Plan 02: Secure Defaults Summary

**Dedicated ops-token protection for telemetry routes, admin-gated raw run/artifact expansions, and sanitized artifact provenance**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-16T20:48:18Z
- **Completed:** 2026-04-16T20:55:09Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- Added a required `EDGAR_BACKEND_OPS_API_TOKEN` setting plus a dedicated bearer dependency that now protects `/metrics` and `/v1/worker/health` without changing `/health` or `/ready`.
- Tightened owner-scoped run and artifact routes so `include_payloads=true` and `include_meta=true` now require an admin user while default summary responses stay unchanged.
- Stopped persisting absolute artifact `source_path` values and replaced them with sanitized `source_filename` and run-workspace-relative provenance where available.

## Task Commits

Each task was committed atomically:

1. **Task 1: Protect ops-only routes with a dedicated bearer token** - `1fa98af` (test), `ef04fd9` (feat)
2. **Task 2: Gate raw expansions to admins and sanitize persisted artifact provenance** - `3ee0d2f` (test), `eebf465` (feat)

**Plan metadata:** recorded in the final docs commit after summary/state updates.

## Files Created/Modified

- `backend/config/settings.py` - Requires a non-empty ops API token as part of secure-default startup validation.
- `backend/api/auth_deps.py` - Adds the ops bearer dependency and a reusable admin-only debug-access guard.
- `backend/api/routes/metrics.py` and `backend/api/routes/health.py` - Protect telemetry endpoints with the dedicated ops token.
- `backend/api/routes/runs.py` and `backend/api/routes/artifacts.py` - Require admin privilege before returning raw payload or metadata expansions.
- `backend/services/artifact_service.py` - Persists sanitized artifact provenance instead of absolute source paths.
- `tests/test_secure_defaults_api.py` - Covers ops-token protection plus non-admin `403` versus admin `200` on raw expansion flags.
- `tests/test_backend_health.py`, `tests/test_artifact_storage.py`, and `tests/test_run_isolation_execution_service.py` - Lock the protected route behavior and sanitized provenance contract.
- `tests/test_api_phase_a.py` and `tests/test_sprint3_transparency_api.py` - Move existing raw-payload assertions onto admin-owned fixtures so they remain valid under the new gate.

## Decisions Made

- Used a second bearer token for ops routes instead of user JWTs so infrastructure access stays separate from application ownership.
- Left summary-first route shapes intact and only gated the existing raw-expansion query flags to minimize compatibility risk.
- Kept artifact provenance useful for audits by storing basename and run-relative path when possible, rather than stripping provenance entirely.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated existing raw-payload tests to use admin fixtures**
- **Found during:** Task 2 (Gate raw expansions to admins and sanitize persisted artifact provenance)
- **Issue:** Existing regressions in `tests/test_api_phase_a.py` and `tests/test_sprint3_transparency_api.py` requested `include_payloads=true` with non-admin users and failed once the new admin gate landed.
- **Fix:** Switched those fixtures to bootstrap-admin users so they still verify raw payload behavior through the intended privileged path.
- **Files modified:** `tests/test_api_phase_a.py`, `tests/test_sprint3_transparency_api.py`
- **Verification:** `python3 -m pytest tests/test_backend_health.py tests/test_secure_defaults_api.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py tests/test_sprint3_transparency_api.py tests/test_api_phase_a.py -q`
- **Committed in:** `eebf465` (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation kept existing raw-payload regressions aligned with the new privileged-access contract. No product scope expansion.

## Issues Encountered

- Parallel `git add` calls briefly contended on `.git/index.lock`. Resolved by restaging the affected files serially and continuing without touching unrelated worktree changes.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 now has its core secure-default posture for bootstrap auth, ops telemetry, raw expansion access, and artifact provenance.
- Plan `03-03` can focus on operator-facing documentation and any remaining security guidance rather than adding new privilege seams.

## Self-Check: PASSED

- Verified `.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md` exists.
- Verified task commits `1fa98af`, `ef04fd9`, `3ee0d2f`, and `eebf465` exist in git history.
