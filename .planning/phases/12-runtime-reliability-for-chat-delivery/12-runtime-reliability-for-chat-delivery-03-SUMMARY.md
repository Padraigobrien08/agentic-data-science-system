---
phase: 12-runtime-reliability-for-chat-delivery
plan: 03
subsystem: onboarding
tags: [auth, onboarding, secure-defaults, chat]
requires:
  - phase: 12-02
    provides: "Sync-first chat delivery and truthful public runtime posture"
provides:
  - "A coarse public auth-capability contract for first-run onboarding surfaces"
  - "Capability-aware login and register pages that stop advertising dead-end registration"
  - "Secure-default registration errors that point users toward bootstrap or sign-in instead of a generic failure"
affects: [backend, frontend, auth, onboarding, tests]
tech-stack:
  added: []
  patterns: ["coarse public auth capabilities", "server-rendered onboarding guidance", "secure-default capability fallback"]
key-files:
  created:
    - .planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-03-SUMMARY.md
    - frontend/src/components/auth/auth-entry-guidance.tsx
    - frontend/src/components/auth/auth-entry-guidance.test.tsx
  modified:
    - backend/api/routes/auth.py
    - backend/schemas/auth.py
    - frontend/src/lib/api/types.ts
    - frontend/src/lib/api/runs.ts
    - frontend/src/actions/auth.ts
    - frontend/src/app/login/page.tsx
    - frontend/src/app/register/page.tsx
    - frontend/src/components/auth/register-form.tsx
    - tests/test_auth_api.py
    - tests/test_secure_defaults_api.py
key-decisions:
  - "Kept the capability surface intentionally coarse: open registration, bootstrap required, and bootstrap completed are enough for truthful onboarding without exposing secrets or operator-only detail."
  - "Used server-rendered capability fetches on login and register so first-run guidance is correct before the user submits anything."
  - "Fell back conservatively to sign-in-only when capability fetches fail, because secure-default onboarding should avoid advertising registration paths it cannot guarantee."
patterns-established:
  - "Public onboarding pages can consume coarse capability contracts while detailed secure-default behavior remains enforced by the backend routes."
  - "Registration failures should echo the current environment posture, not a generic dead-end message."
requirements-completed: [RUN-03]
completed: 2026-04-18
---

# Phase 12: Runtime Reliability for Chat Delivery Summary

**Capability-aware onboarding for secure-default local stacks**

## Accomplishments

- Added `GET /v1/auth/capabilities` with a small public contract that tells the frontend whether registration is open, bootstrap is still required, or the environment has moved to sign-in-only mode.
- Extended backend auth regressions so open registration, secure-default pre-bootstrap, and secure-default post-bootstrap states are all locked to the new capability contract.
- Added `AuthEntryGuidance` and rewired the login and register pages to fetch capabilities server-side, removing the unconditional “Create one” path from the login page and suppressing the dead-end registration form when self-registration is closed.
- Updated the registration action and form messaging so a disabled registration response now points the user toward bootstrap or sign-in depending on the environment instead of returning one generic error.

## Verification

- `python3 -m pytest tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short`
- `cd frontend && npm run test -- src/components/auth/auth-entry-guidance.test.tsx`
- `cd frontend && npm run build`

## Notes

- The new guidance component is intentionally narrow and presentational: it solves the first-run secure-default confusion uncovered during live chat testing without broadening into a full auth redesign.
- The conservative fallback on capability-fetch failure is deliberate. In a locked-down environment, showing sign-in-only guidance is safer than advertising registration that may not actually be available.
