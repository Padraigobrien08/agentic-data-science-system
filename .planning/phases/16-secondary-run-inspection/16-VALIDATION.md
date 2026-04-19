---
phase: 16
slug: secondary-run-inspection
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 16 - Validation Strategy

> Per-phase validation contract for reducing the standalone run page into a secondary verification surface.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` |
| **Full suite command** | `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~10 seconds quick, ~35 seconds full |

## Sampling Rate

- **After every task commit:** run the focused vitest command for the touched run-page seam
- **After every plan wave:** run the quick command above
- **Before phase closeout:** full suite and production build must be green
- **Max feedback latency:** 20 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01 | 01 | 1 | NAV-03 | component/page framing | `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` | ❌ new | ⬜ pending |
| 16-02 | 02 | 2 | NAV-03 | duplication reduction | `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx` | ⚠️ extend new | ⬜ pending |
| 16-03 | 03 | 3 | NAV-03 | regression/build | `cd frontend && npm run test -- src/components/runs/run-inspection-panel.test.tsx src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | ⚠️ extend new | ⬜ pending |

## Wave 0 Requirements

- [ ] Add `frontend/src/components/runs/run-inspection-panel.test.tsx` — verification-first run-page composition and copy
- [ ] Extend or cover removal of duplicated findings/confidence/evidence reading sections
- [ ] Close with the frontend production build

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The standalone run page now feels like a verification surface and clearly returns the user to chat for answer reading | NAV-03 | Requires the live app and subjective confirmation of page role | 1. Open a completed run from chat. 2. Confirm the page emphasizes verification and includes a clear return-to-chat action. 3. Confirm the full answer narrative does not dominate the page anymore. |

## Validation Sign-Off

- [ ] All planned tasks have automated verification commands or explicit Wave 0 gaps
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification
- [ ] Wave 0 adds run-page component coverage
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
