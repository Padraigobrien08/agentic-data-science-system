---
phase: 12
slug: runtime-reliability-for-chat-delivery
status: planned
nyquist_compliant: true
wave_0_complete: false
created: 2026-04-18
---

# Phase 12 - Validation Strategy

> Per-phase validation contract for worker/runtime stability, sync-first chat delivery, truthful degraded status, and first-run auth/onboarding cleanup.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest 8.4.2` + `vitest` |
| **Config file** | `pytest.ini` and `frontend/vitest.config.ts` |
| **Quick run command** | `python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short && cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/auth/register-form.test.tsx` |
| **Full suite command** | `python3 -m pytest tests/test_backend_health.py tests/test_worker_lease_heartbeat.py tests/test_worker_job_lifecycle.py tests/test_async_run_queue.py tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short && cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/auth/register-form.test.tsx && npm run build` |
| **Estimated runtime** | ~20 seconds quick, ~60 seconds full |

## Sampling Rate

- **After every task commit:** Run the focused pytest or vitest command for the touched seam
- **After every plan wave:** Run the quick command above
- **Before `$gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01 | 01 | 1 | RUN-01, RUN-02 | backend/runtime | `python3 -m pytest tests/test_worker_lease_heartbeat.py tests/test_async_run_queue.py tests/test_worker_job_lifecycle.py -q --tb=short` | ⚠️ extend existing | ⬜ pending |
| 12-02 | 02 | 2 | RUN-03 | frontend/backend | `python3 -m pytest tests/test_backend_health.py -q --tb=short && cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx` | ❌ Wave 0 | ⬜ pending |
| 12-03 | 03 | 3 | RUN-03 | auth/frontend | `python3 -m pytest tests/test_auth_api.py tests/test_secure_defaults_api.py -q --tb=short && cd frontend && npm run test -- src/components/auth/register-form.test.tsx` | ⚠️ extend existing / ❌ Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [ ] `tests/test_worker_lease_heartbeat.py` or a new worker boot smoke test — explicit regression for the circular-import startup path
- [ ] `tests/test_async_run_queue.py` / `tests/test_worker_job_lifecycle.py` — queue claim still works after the import-boundary repair
- [ ] `tests/test_backend_health.py` — public coarse background-delivery status plus existing ops truthfulness
- [ ] `frontend/src/components/chat-shell/chat-composer.test.tsx` — sync-only/default behavior and hidden/de-emphasized queue affordance
- [ ] `frontend/src/components/chat-shell/chat-shell.test.tsx` and/or `chat-message-list.test.tsx` — workspace-level and per-message fallback/degraded-state rendering
- [ ] `frontend/src/components/auth/register-form.test.tsx` — environment-aware registration/bootstrap guidance

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Documented Compose stack supports first-run chat delivery end-to-end | RUN-01, RUN-02, RUN-03 | Requires the actual local multi-container stack, browser sign-in flow, and live runtime surfaces | 1. Rebuild `docker compose` for the documented stack. 2. Sign in through the web app. 3. Submit a chat prompt. 4. Confirm the run executes without workspace-permission failure. 5. Confirm the chat workspace shows the current delivery-mode status truthfully. |

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 gaps
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 names the missing frontend/runtime coverage references
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
