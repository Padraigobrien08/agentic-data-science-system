---
phase: 17
slug: narrative-answer-contract
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-19
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for backend-safe narrative preview fields, narrative-first chat answers, and graceful fallback behavior.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` + `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx` |
| **Full suite command** | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~18 seconds quick, ~45 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the most focused backend or frontend command for the seam that changed
- **After every plan wave:** Run the quick run command above
- **Before `$gsd-verify-work`:** Full suite and frontend build must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 17-01 | 01 | 1 | ANSR-01, ANSR-02 | backend contract | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` | ⚠️ extend existing | ⬜ pending |
| 17-02 | 02 | 2 | ANSR-01, ANSR-02 | frontend view-model | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts` | ⚠️ extend existing | ⬜ pending |
| 17-03 | 03 | 3 | ANSR-01, ANSR-02 | rendering/build | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

---

## Wave 0 Requirements

- [x] Extend `tests/test_run_transparency_builders.py` — narrative preview fields and explicit fallback-safe outputs
- [x] Extend `tests/test_sprint3_transparency_api.py` — transparency API exposes the new narrative fields
- [x] Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` — narrative preview is preferred over `summaryLine`, and fallback remains explicit
- [x] Extend `frontend/src/lib/chat-run-history.test.ts` and `frontend/src/actions/runs.test.ts` — live replies and hydrated history use the same narrative-first contract
- [x] Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` — rendered chat answers prioritize prose and keep limited-support replies readable

*Existing infrastructure covers all Phase 17 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A completed analysis reads like a substantive analyst reply in chat instead of a headline summary card | ANSR-01 | Requires visual review of real prose hierarchy and reading flow | 1. Open a project chat workspace. 2. Submit a supported analysis request. 3. Confirm the completed assistant message reads as a multi-paragraph analyst answer with a lead thesis and prose body rather than a one-line summary plus dominant cards. |
| A weak-support run still returns a readable partial answer instead of placeholder success text | ANSR-02 | Requires end-to-end observation of limited-evidence behavior in the real UI | 1. Trigger a prompt or fixture that yields limited support. 2. Confirm the answer still returns prose that states what can be said and what evidence is missing or weak. 3. Confirm the UI does not display generic “completed without a summary line” or similarly vague copy as the main answer. |

---

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers backend preview construction, API exposure, answer-view derivation, history compatibility, and chat rendering
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
