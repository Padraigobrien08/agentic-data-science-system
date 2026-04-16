---
phase: 03
slug: secure-defaults
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-16
---

# Phase 03 - Validation Strategy

> Per-phase validation contract for secure-default work.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` 8.4.2 |
| **Config file** | `pytest.ini` |
| **Quick run command** | `python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q` |
| **Full suite command** | `python3 -m pytest tests/ -q --tb=short` |
| **Estimated runtime** | ~10 seconds quick, ~90 seconds full |

## Sampling Rate

- **After every task commit:** run the task-local `<automated>` command from the active plan
- **After every plan wave:** run `python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q`
- **Before `$gsd-execute-phase 3` completion:** rerun the full quick command plus any docs/frontend checks introduced by Plan 03-03
- **Max feedback latency:** 10 seconds for backend regressions

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01 | 01 | 1 | SECU-01, SECU-02 | unit + API integration | `python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py -q` | ❌ | ⬜ pending |
| 03-02 | 02 | 2 | SECU-03 | API integration + persistence | `python3 -m pytest tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q` | ❌ | ⬜ pending |
| 03-03 | 03 | 3 | SECU-01, SECU-02, SECU-03 | integration + docs regression | `python3 -m pytest tests/test_secure_defaults_settings.py tests/test_auth_api.py tests/test_secure_defaults_api.py tests/test_backend_health.py tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q` | ❌ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

## Wave 0 Requirements

- [ ] `tests/test_secure_defaults_settings.py` - built-in JWT-secret rejection and explicit dev escape hatch coverage
- [ ] `tests/test_secure_defaults_api.py` - bootstrap-admin flow, ops-token protection, and admin-only raw expansion coverage
- [ ] Existing auth and artifact tests updated to stop assuming default-open registration and absolute `source_path`
- [ ] Compose/docs surfaces updated so secure env requirements are explicit and testable

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Local stack starts only when required security env vars are set | SECU-01, SECU-02, SECU-03 | Compose and docs behavior must match real operator setup, not just unit tests | 1. Copy `.env.example` to `.env`. 2. Remove `EDGAR_BACKEND_JWT_SECRET` or `EDGAR_BACKEND_OPS_API_TOKEN` and confirm startup fails clearly. 3. Restore values and confirm `docker compose up` succeeds. |
| Bootstrap + ops-route usage is understandable from docs | SECU-02, SECU-03 | Human-facing setup quality is a docs/UX concern | 1. Follow `docs/auth-api.md` to create the first admin. 2. Follow `docs/local-stack.md` to call `/metrics` with the ops token. 3. Confirm the steps work without hidden assumptions. |

## Validation Sign-Off

- [x] All planned tasks have automated verification commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 names the missing security-specific regression files
- [x] No watch-mode commands
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
