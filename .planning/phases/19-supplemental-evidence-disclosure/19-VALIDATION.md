---
phase: 19
slug: supplemental-evidence-disclosure
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-24
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for answer-first evidence disclosure, unified slim evidence rows, and limited-evidence fallback behavior.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx` |
| **Full suite command** | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~12 seconds quick, ~30 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the most focused `vitest` command for the seam that changed
- **After every plan wave:** Run the quick command above
- **Before `$gsd-verify-work`:** Full suite and `npm run build` must be green
- **Max feedback latency:** 20 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01 | 01 | 1 | ANSR-03, EVID-01 | renderer hierarchy | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 19-02 | 02 | 2 | EVID-02 | view-model + renderer | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 19-03 | 03 | 3 | EVID-03 | renderer/build | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

---

## Wave 0 Requirements

- [x] Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` — unified supplemental evidence rows and limited-evidence state derivation
- [x] Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` — collapsed-by-default disclosure, slim evidence-row rendering, and persistent secondary pills
- [x] Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` — hydrated history still renders correctly with the new disclosure model
- [x] Reuse existing build gate — layout and disclosure changes must pass `npm run build`

*Existing frontend infrastructure covers all Phase 19 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The answer still reads cleanly before any evidence is opened | ANSR-03, EVID-01 | Requires visual judgment about narrative dominance and disclosure weight | 1. Open a completed narrative answer. 2. Confirm the answer reads as the main content before opening the disclosure. 3. Confirm the disclosure affordance is present but not visually dominant. |
| Supplemental evidence rows feel wide and lightweight instead of like stacked utility cards | EVID-02 | Requires visual review of row density, width use, and exact-jump affordance clarity | 1. Open the disclosure for a run with multiple evidence items. 2. Confirm each row is horizontally wide, vertically thin, and includes one clear reason it matters plus one exact jump. |
| Thin-evidence cases remain explicit and navigable | EVID-01, EVID-02 | Requires checking the product language and state behavior when support is sparse | 1. Open a run with weak or missing support. 2. Confirm the disclosure still exists. 3. Confirm opening it explains the limitation rather than showing nothing. |

---

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers hierarchy, merged row derivation, and limited-evidence disclosure behavior
- [x] No watch-mode flags
- [x] Feedback latency < 20s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
