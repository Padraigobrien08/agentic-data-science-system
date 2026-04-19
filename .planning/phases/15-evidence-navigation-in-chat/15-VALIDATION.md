---
phase: 15
slug: evidence-navigation-in-chat
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 15 - Validation Strategy

> Per-phase validation contract for inline findings, confidence, caveats, and compact evidence navigation inside the chat-native answer.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx` |
| **Full suite command** | `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~15 seconds quick, ~35 seconds full |

## Sampling Rate

- **After every task commit:** run the focused vitest command for the touched chat seam
- **After every plan wave:** run the quick command above
- **Before phase closeout:** full suite and production build must be green
- **Max feedback latency:** 20 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01 | 01 | 1 | CHAT-02, NAV-01 | action/view-model | `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts` | ⚠️ extend existing | ⬜ pending |
| 15-02 | 02 | 2 | CHAT-02, NAV-01 | component rendering | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 15-03 | 03 | 3 | NAV-02 | interaction/build | `cd frontend && npm run test -- src/actions/runs.test.ts src/lib/chat-run-history.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [ ] Extend `frontend/src/actions/runs.test.ts` — supported replies include richer answer data for findings, confidence, caveats, and compact nav
- [ ] Extend `frontend/src/lib/chat-run-history.test.ts` — hydrated history reuses the richer chat answer contract
- [ ] Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` — inline findings, confidence/caveats, and compact nav render in chat
- [ ] Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` — the richer assistant card still upgrades in place and preserves one visible thread

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A completed chat answer can be read and first-pass verified without leaving chat | CHAT-02, NAV-01 | Requires a live signed-in workspace and actual run output | 1. Open a project chat page. 2. Submit a supported prompt. 3. Wait for completion. 4. Confirm the chat card shows findings, confidence, caveats, and a compact evidence navigation area inline. |
| Finding-level and caveat-level secondary jumps land in the correct artifact or trace target | NAV-02 | Requires real navigation in the running app | 1. From a completed answer, use one finding-level or caveat-level secondary link. 2. Confirm it lands on the specific artifact or trace anchor expected. 3. Return to chat and verify the transcript remains intact. |

## Validation Sign-Off

- [ ] All planned tasks have automated verification commands or explicit Wave 0 gaps
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification
- [ ] Wave 0 covers the richer answer contract, hydrated history, and inline rendering
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
