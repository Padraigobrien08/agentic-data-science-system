---
phase: 03-secure-defaults
plan: 01
subsystem: auth
tags: [jwt, bootstrap, fastapi, sqlalchemy, alembic, pytest]
requires:
  - phase: 02-worker-resilience
    provides: authenticated run and project flows that now need secure-default enforcement
provides:
  - fail-fast startup validation for unsafe JWT and registration settings
  - default-closed registration with explicit bootstrap-admin onboarding
  - persisted and exposed user admin capability for later privileged access controls
affects: [03-secure-defaults-02, 03-secure-defaults-03, auth, ops]
tech-stack:
  added: []
  patterns:
    - explicit insecure-dev opt-in for built-in secrets
    - one-time token-guarded bootstrap admin route
    - persisted is_admin capability on users
key-files:
  created:
    - alembic/versions/008_user_admin_bootstrap.py
    - tests/test_secure_defaults_settings.py
  modified:
    - backend/config/settings.py
    - backend/models/user.py
    - backend/schemas/user.py
    - backend/services/user_service.py
    - backend/schemas/auth.py
    - backend/api/routes/auth.py
    - tests/conftest.py
    - tests/api_auth.py
    - tests/test_auth_api.py
key-decisions:
  - "Reject the built-in JWT secret by exact value unless EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true is set explicitly."
  - "Close self-service registration by default and require a dedicated X-EDGAR-Bootstrap-Token flow for the first admin."
  - "Persist is_admin on users now so later Phase 3 plans can gate privileged payload and ops access without redesigning auth."
patterns-established:
  - "Settings validators own secure-default startup posture, while tests opt into legacy-open behavior explicitly through env."
  - "Bootstrap onboarding is a separate public route that succeeds only once and returns normal UserRead payloads."
requirements-completed: [SECU-01, SECU-02]
duration: 6min
completed: 2026-04-16
---

# Phase 03 Plan 01: Secure Defaults Summary

**Secure startup validation and one-time bootstrap-admin onboarding for the existing JWT auth stack**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-16T20:36:00Z
- **Completed:** 2026-04-16T20:41:54Z
- **Tasks:** 2
- **Files modified:** 11

## Accomplishments

- Added fail-fast settings validation that rejects the built-in JWT secret unless the explicit insecure-dev override is enabled.
- Closed self-service registration by default and required a bootstrap token when that posture is active.
- Added persisted `is_admin` support plus a one-time `/v1/auth/bootstrap` route that creates only the first admin and exposes that capability through `/v1/auth/me`.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add secure settings validation and persisted admin capability** - `6993d80` (test), `4cba73b` (feat)
2. **Task 2: Replace default-open onboarding with explicit bootstrap-admin flow** - `0faeea1` (test), `d813e90` (feat)

**Plan metadata:** recorded in the final docs commit after summary/state updates.

## Files Created/Modified

- `alembic/versions/008_user_admin_bootstrap.py` - Adds the persisted `users.is_admin` column with a safe default.
- `backend/config/settings.py` - Enforces the secure-default JWT and bootstrap-token contract.
- `backend/models/user.py` - Persists `is_admin` on user rows.
- `backend/schemas/user.py` - Returns `is_admin` in auth/user responses.
- `backend/services/user_service.py` - Allows user creation flows to mark admins explicitly.
- `backend/schemas/auth.py` - Adds the bootstrap request body.
- `backend/api/routes/auth.py` - Implements the one-time bootstrap route and closed-registration behavior.
- `tests/conftest.py` - Keeps the broad legacy test environment explicit after the secure defaults flipped.
- `tests/test_secure_defaults_settings.py` - Covers the startup validation and default registration posture.
- `tests/api_auth.py` - Adds bootstrap-based auth/project helpers for API tests.
- `tests/test_auth_api.py` - Covers registration-disabled, bootstrap success, and second-bootstrap rejection paths.

## Decisions Made

- Kept the existing JWT + owner-scoped auth model and added only the minimal new privilege surface needed for Phase 3: a persisted `is_admin` flag.
- Required the insecure-dev JWT escape hatch to be explicit and narrow instead of inferring it from debug or deployment heuristics.
- Made bootstrap a first-admin-only route so closing registration does not silently leave another long-lived open onboarding path.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Parallel `git add` commands created transient `.git/index.lock` contention. Resolved by staging remaining files serially; no code or planning artifacts were lost.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Phase 3 now has the auth primitives needed for the next plan to gate privileged payload/meta access and ops-only endpoints.
- Existing test helpers remain compatible because the legacy-open posture is now an explicit test env choice instead of a product default.

## Self-Check: PASSED

- Verified `.planning/phases/03-secure-defaults/03-secure-defaults-01-SUMMARY.md` exists.
- Verified task commits `6993d80`, `4cba73b`, `0faeea1`, and `d813e90` exist in git history.
