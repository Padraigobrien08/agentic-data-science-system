---
phase: 14-chat-native-result-contract
verified: 2026-04-19T09:43:00Z
status: passed
score: 3/3 must-haves verified
---

# Phase 14: Chat-Native Result Contract Verification Report

**Phase Goal:** Completed run results become first-class chat answers with stable run linkage so the workspace conversation becomes the primary answer-reading surface.
**Verified:** 2026-04-19T09:43:00Z
**Status:** passed
**Re-verification:** No - initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
| --- | --- | --- | --- |
| 1 | Completed analyses now render their primary answer directly inside workspace chat through a compact structured card rather than plain assistant prose and link-out instructions. | ✓ VERIFIED | `frontend/src/actions/runs.ts`, `frontend/src/lib/run-primary-view.ts`, `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, `frontend/src/components/chat-shell/chat-message-list.tsx`, `frontend/src/actions/runs.test.ts`, `frontend/src/components/chat-shell/chat-message-list.test.tsx` |
| 2 | Workspace chat now reloads into a persisted run-backed transcript and continues as one visible thread instead of fake local conversation tabs. | ✓ VERIFIED | `frontend/src/lib/chat-run-history.ts`, `frontend/src/app/projects/[projectId]/chat/page.tsx`, `frontend/src/components/chat-shell/chat-shell.tsx`, `frontend/src/components/chat-shell/chat-sidebar.tsx`, `frontend/src/lib/chat-run-history.test.ts`, `frontend/src/components/chat-shell/chat-shell.test.tsx` |
| 3 | Each completed chat answer now carries one compact run identity strip with stable run linkage and no legacy run-answer/deep-dive/all-runs footer sprawl. | ✓ VERIFIED | `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, `frontend/src/components/chat-shell/chat-message-list.tsx`, `frontend/src/components/chat-shell/chat-message-list.test.tsx`, `frontend/src/app/projects/[projectId]/chat/page.tsx` |

**Score:** 3/3 truths verified

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
| --- | --- | --- | --- |
| Focused frontend regression gate | `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` | `7 passed` | ✓ PASS |
| Frontend production build | `cd frontend && npm run build` | passed | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
| --- | --- | --- | --- | --- |
| `CHAT-01` | `14-01`, `14-02`, `14-03` | User can receive the completed analysis answer as a workspace chat message instead of using the standalone run page as the primary place to read the result | ✓ SATISFIED | Structured answer contract in `frontend/src/actions/runs.ts`, compact card rendering in `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, and inline-first page copy in `frontend/src/app/projects/[projectId]/chat/page.tsx` |
| `CHAT-03` | `14-02`, `14-03` | User can continue the workspace conversation after a completed run while retaining visible linkage to the run that produced the answer | ✓ SATISFIED | Persisted transcript hydration in `frontend/src/lib/chat-run-history.ts`, one-thread shell in `frontend/src/components/chat-shell/chat-shell.tsx`, and run strip linkage in `frontend/src/components/chat-shell/chat-run-answer-card.tsx` |

### Gaps Summary

No blocking gaps remain for Phase 14. The next work is Phase 15: attach findings, caveats, and compact evidence navigation to the inline chat answer without regressing the now-stable chat-native answer shell.

---

_Verified: 2026-04-19T09:43:00Z_
_Verifier: Codex_
