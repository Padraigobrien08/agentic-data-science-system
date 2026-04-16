---
phase: 03-secure-defaults
verified: 2026-04-16T21:15:11Z
status: human_needed
score: 9/9 must-haves verified
human_verification:
  - test: "Compose env fail-fast"
    expected: "With missing JWT, ops, or bootstrap secrets, the documented local stack fails clearly; with valid values, the stack starts successfully."
    why_human: "Requires starting the real Docker Compose stack and observing operator-facing failure and recovery behavior."
  - test: "Bootstrap and ops docs walkthrough"
    expected: "Following docs/auth-api.md and docs/local-stack.md creates the first admin and reaches /metrics and /v1/worker/health with the ops bearer token."
    why_human: "Documentation usability and live endpoint behavior require an end-to-end operator run."
  - test: "Register page UX"
    expected: "The register page and disabled-registration error copy are clear in the rendered web flow."
    why_human: "Rendered copy clarity and flow comprehension are UX checks, not static-code assertions."
---

# Phase 3: Secure Defaults Verification Report

**Phase Goal:** Eliminate insecure production defaults and reduce exposure of sensitive operational data.
**Verified:** 2026-04-16T21:15:11Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Startup fails when the built-in JWT secret is active unless the explicit insecure-dev override is enabled. | ✓ VERIFIED | `backend/config/settings.py:297-316` rejects `BUILTIN_DEV_JWT_SECRET`; `backend/main.py:37-45` loads settings during app creation/startup; `tests/test_secure_defaults_settings.py` and `python3 -m pytest tests/test_secure_defaults_settings.py::test_built_in_secret_rejected_by_default -q` passed. |
| 2 | Self-service registration is disabled by default instead of default-open. | ✓ VERIFIED | `backend/config/settings.py:43-53` defaults `allow_open_registration=False`; `backend/api/routes/auth.py:24-31` returns `403 Registration is disabled`; `tests/test_auth_api.py` covers the closed-registration path. |
| 3 | Operators can create the first admin through an explicit bootstrap route rather than relying on open registration. | ✓ VERIFIED | `backend/api/routes/auth.py:49-79` defines `POST /v1/auth/bootstrap`; `backend/models/user.py:30`, `backend/schemas/user.py:24-31`, and `backend/services/user_service.py:21-39` persist and return `is_admin`; targeted bootstrap test passed. |
| 4 | `/metrics` and `/v1/worker/health` reject requests without the dedicated ops token. | ✓ VERIFIED | `backend/api/auth_deps.py:62-88` defines ops bearer validation; `backend/api/routes/metrics.py:16-21` and `backend/api/routes/health.py:56-90` depend on `OpsTokenDep`; `tests/test_backend_health.py` and `tests/test_secure_defaults_api.py` passed. |
| 5 | Raw payload or meta expansions on owner routes require an admin user instead of any resource owner. | ✓ VERIFIED | `backend/api/routes/runs.py:198-307` and `backend/api/routes/artifacts.py:190-198` call `require_admin_debug_access`; `backend/api/auth_deps.py:82-85` enforces the gate; non-admin and admin expansion tests passed. |
| 6 | Artifact provenance no longer persists absolute filesystem `source_path` values. | ✓ VERIFIED | `backend/services/artifact_service.py:224-277` writes `source_filename` and optional `source_workspace_relative_path`, not `source_path`; `tests/test_artifact_storage.py`, `tests/test_run_isolation_execution_service.py`, and `tests/test_secure_defaults_api.py` assert the sanitized metadata. |
| 7 | The documented local stack no longer ships a baked-in JWT secret or default-open registration. | ✓ VERIFIED | `.env.example` requires `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_OPS_API_TOKEN`, and `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`; `docker-compose.yml` uses required substitutions and defaults `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION` to `false`. |
| 8 | Operators have explicit instructions for bootstrap-admin creation and ops-token access. | ✓ VERIFIED | `docs/auth-api.md` documents `/v1/auth/bootstrap`, `Registration is disabled`, admin-only raw expansions, and ops-token access; `docs/local-stack.md` requires copying `.env.example` and using the ops bearer token; `docs/artifact-delivery.md` documents sanitized artifact provenance. |
| 9 | User-facing registration guidance matches the new closed-by-default backend behavior. | ✓ VERIFIED | `frontend/src/actions/auth.ts:110-114` maps the backend `403` detail to explicit operator guidance; `frontend/src/app/register/page.tsx:23-31` says registration is usually disabled by default; `frontend/src/lib/api/types.ts:26-34` mirrors backend `is_admin`. |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
| --- | --- | --- | --- |
| `backend/config/settings.py` | Fail-fast security-default settings contract for JWT secret, onboarding posture, bootstrap token, and ops token | ✓ VERIFIED | Fields and validator branches are present and exercised by tests. |
| `backend/api/routes/auth.py` | Closed-by-default registration and explicit bootstrap-admin route | ✓ VERIFIED | Public `/register`, `/bootstrap`, `/login`, and `/me` flows are implemented with the expected failure modes. |
| `tests/test_secure_defaults_settings.py` | Regression coverage for startup validation and default registration posture | ✓ VERIFIED | Four focused settings regressions exist and passed. |
| `backend/api/auth_deps.py` | Dedicated ops-token dependency plus admin-only raw expansion helper | ✓ VERIFIED | `get_ops_token`, `require_ops_token`, and `require_admin_debug_access` are implemented and used. |
| `backend/services/artifact_service.py` | Sanitized artifact provenance persistence | ✓ VERIFIED | Pipeline ingest stores basename and run-relative provenance instead of absolute paths. |
| `tests/test_secure_defaults_api.py` | Ops-token and admin-only raw access regressions | ✓ VERIFIED | Substantive API tests cover registration closure, bootstrap, ops auth, admin gating, and sanitized provenance. |
| `docker-compose.yml` | Secure local-stack env contract without insecure secret fallbacks | ✓ VERIFIED | Required secret substitutions and closed-by-default registration are wired into the backend env block. |
| `docs/auth-api.md` | Bootstrap-admin, registration-defaults, and ops-token usage guide | ✓ VERIFIED | Operator-facing auth contract matches the backend routes and response details. |
| `frontend/src/actions/auth.ts` | User-facing registration-disabled guidance aligned with backend defaults | ✓ VERIFIED | Server action rewrites the exact backend error into operator guidance. |

### Key Link Verification

| From | To | Via | Status | Details |
| --- | --- | --- | --- | --- |
| `backend/config/settings.py` | `backend/api/routes/auth.py` | `bootstrap_admin_token` and `allow_open_registration` drive route behavior directly | ✓ WIRED | `auth.register()` reads `allow_open_registration`; `auth.bootstrap_admin()` reads `bootstrap_admin_token`. |
| `backend/models/user.py` | `backend/schemas/user.py` | `is_admin` persists and is returned through auth routes | ✓ WIRED | `User.is_admin` maps to `UserRead.is_admin`; `/v1/auth/me` uses `response_model=UserRead`. |
| `tests/test_auth_api.py` | `backend/api/routes/auth.py` | Registration-disabled and bootstrap regressions lock the onboarding contract | ✓ WIRED | Tests assert `403 Registration is disabled`, bootstrap success, and `409 Bootstrap already completed`. |
| `backend/api/routes/metrics.py` | `backend/api/auth_deps.py` | Ops-only dependency protects the public infra route | ✓ WIRED | `prometheus_metrics(..., _ops_token: OpsTokenDep)` requires the dedicated ops bearer token. |
| `backend/api/routes/runs.py` | `backend/api/auth_deps.py` | Summary-first owner routes require admin capability before honoring `include_payloads` | ✓ WIRED | `get_run`, `list_run_steps`, and `list_run_model_calls` call `require_admin_debug_access()` when expansions are requested. |
| `backend/services/artifact_service.py` | `tests/test_run_isolation_execution_service.py` | Sanitized provenance replaces absolute `source_path` in persisted artifact metadata | ✓ WIRED | Test asserts `source_filename`, `source_workspace_relative_path`, and absence of `source_path`. |
| `.env.example` | `docker-compose.yml` | Required env names match compose substitutions exactly | ✓ WIRED | JWT, ops, bootstrap, and registration env names match across both files. |
| `docs/auth-api.md` | `backend/api/routes/auth.py` | Bootstrap curl examples and registration posture reflect the route contract | ✓ WIRED | Docs reference `/v1/auth/bootstrap`, `Registration is disabled`, and admin-only expansions exactly as implemented. |
| `frontend/src/actions/auth.ts` | `backend/api/routes/auth.py` | Disabled-registration guidance maps the backend `403` detail into operator-facing copy | ✓ WIRED | Server action rewrites the exact backend `Registration is disabled` detail string. |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
| --- | --- | --- | --- | --- |
| `backend/api/routes/auth.py` | `allow_open_registration`, `configured_bootstrap_token`, `User.is_admin` | `get_settings()` env-backed settings + `UserService`/DB rows | Yes | ✓ FLOWING |
| `backend/api/routes/metrics.py` | `_ops_token` | `get_ops_token()` -> `settings.ops_api_token` | Yes | ✓ FLOWING |
| `backend/api/routes/runs.py` | `include_payloads`, `user.is_admin` | Request query params + JWT-authenticated `CurrentUserDep` from DB | Yes | ✓ FLOWING |
| `backend/services/artifact_service.py` | `provenance_meta` | Resolved file path + `settings.run_workspace_root` + `analysis_run_id` | Yes | ✓ FLOWING |
| `frontend/src/actions/auth.ts` | `detail` / returned `error` | Real backend `POST /v1/auth/register` response text | Yes | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Built-in JWT secret is rejected by default | `python3 -m pytest tests/test_secure_defaults_settings.py::test_built_in_secret_rejected_by_default -q` | `1 passed in 0.13s` | ✓ PASS |
| Bootstrap creates an admin and `/v1/auth/me` returns `is_admin` | `python3 -m pytest tests/test_auth_api.py::test_bootstrap_creates_first_admin_and_me_returns_is_admin -q` | `1 passed in 1.41s` | ✓ PASS |
| Ops token and admin-only raw expansion gates are enforced | `python3 -m pytest tests/test_secure_defaults_api.py::test_non_admin_owner_cannot_request_raw_expansions tests/test_backend_health.py::test_ops_routes_require_ops_bearer_token -q` | `3 passed in 1.49s` | ✓ PASS |
| Phase 03 regression gate stays green | `python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q` | `40 passed in 9.95s` | ✓ PASS |
| Existing raw-payload regressions remain compatible with the new admin gate | `python3 -m pytest tests/test_api_phase_a.py tests/test_sprint3_transparency_api.py -q` | `11 passed in 7.04s` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `SECU-01` | `03-01`, `03-03` | Deployment fails fast when the default JWT secret is still configured outside tests | ✓ SATISFIED | `backend/config/settings.py` rejects the built-in secret unless `EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true`; `backend/main.py` loads settings at startup; settings regression tests passed. |
| `SECU-02` | `03-01`, `03-03` | New deployments keep self-service registration disabled unless an operator explicitly enables it | ✓ SATISFIED | `allow_open_registration` defaults to `false`; `/v1/auth/register` returns `403`; `/v1/auth/bootstrap` creates the first admin; frontend and docs explain the closed-by-default posture. |
| `SECU-03` | `03-02`, `03-03` | Metrics endpoints and persisted sensitive payload fields are protected or redacted by default | ✓ SATISFIED | `/metrics` and `/v1/worker/health` require the ops bearer token; raw run/model/artifact expansions are admin-only; artifact provenance strips absolute paths; API and persistence tests passed. |

Orphaned phase requirements: none. Every Phase 3 requirement in `.planning/REQUIREMENTS.md` appears in the phase plans.

### Anti-Patterns Found

No blocker or warning anti-patterns were found in the scanned phase files. Targeted scans found no TODO/FIXME placeholders, empty stub implementations, or user-visible hardcoded placeholder behavior in the verified artifacts.

### Human Verification Required

### 1. Compose Env Fail-Fast

**Test:** Copy `.env.example` to `.env`, remove one required secret (`EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_OPS_API_TOKEN`, or `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`), then run `docker compose up`.
**Expected:** Compose or backend startup fails clearly. Restoring valid values allows the stack to start.
**Why human:** This requires running the real Compose stack and observing operator-facing startup behavior.

### 2. Bootstrap And Ops Docs Walkthrough

**Test:** Follow `docs/auth-api.md` to bootstrap the first admin, then follow `docs/local-stack.md` to call `/metrics` and `/v1/worker/health` with the ops bearer token.
**Expected:** The documented steps work without undocumented prerequisites.
**Why human:** Documentation clarity and end-to-end operator usability cannot be fully verified from static code inspection.

### 3. Register Page UX

**Test:** Open the register page in the web app and submit against a backend with `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false`.
**Expected:** The page copy and returned error make it clear that registration is disabled by default and point the user to operator/bootstrap action.
**Why human:** Rendered copy comprehension and the full browser flow are UX-level checks.

### Gaps Summary

No automated implementation gaps were found. The codebase satisfies all 9 plan-level must-have truths for Phase 03, the documented quick regression gate passed, and the compatibility regressions for previously touched raw-payload tests also passed. Remaining work is limited to human validation of the live Compose startup behavior, docs walkthrough quality, and rendered registration UX.

---

_Verified: 2026-04-16T21:15:11Z_
_Verifier: Claude (gsd-verifier)_
