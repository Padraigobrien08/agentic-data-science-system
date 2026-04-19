---
phase: 14
slug: chat-native-result-contract
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-19
---

# Phase 14 - Validation Strategy

> Per-phase validation contract for compact chat-native run answers, reload-safe transcript hydration, and stable run linkage.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` |
| **Full suite command** | `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` |
| **Estimated runtime** | ~12 seconds quick, ~35 seconds full |

## Sampling Rate

- **After every task commit:** Run the focused vitest command for the touched chat or answer seam
- **After every plan wave:** Run the quick command above
- **Before `$gsd-verify-work`:** Full suite and production build must be green
- **Max feedback latency:** 20 seconds

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01 | 01 | 1 | CHAT-01 | component/view-model | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 14-02 | 02 | 2 | CHAT-01, CHAT-03 | page/action hydration | `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-shell.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 14-03 | 03 | 3 | CHAT-03 | rendering/build | `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` | ✅ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

## Wave 0 Requirements

- [ ] Extend `frontend/src/actions/runs.test.ts` — compact answer payload returns on supported runs and still upgrades one assistant slot per request
- [ ] Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` — structured answer block and compact run linkage render in completed assistant replies
- [ ] Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` — hydrated history renders on load and pending assistant rows upgrade in place
- [ ] Add or extend a compact answer derivation test around the reused `run-primary-view` seam if the phase introduces a chat-specific subset builder

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Reloading workspace chat still shows recent completed answers inline with stable run linkage | CHAT-01, CHAT-03 | Requires a real signed-in workspace, live run completion, and browser reload | 1. Open a project chat workspace. 2. Submit a supported analysis request and wait for completion. 3. Confirm the assistant message becomes a compact structured answer with a compact run strip. 4. Reload the page and confirm that answer remains visible in the chat history. |
| Follow-up prompts stay in the same visible thread without hidden carry-forward semantics | CHAT-03 | Requires live interaction across multiple prompts | 1. After one completed answer appears, submit a new supported prompt. 2. Confirm a new user message and one new pending/final assistant answer are appended below the earlier answer. 3. Confirm the new request uses the explicit prompt text and current workspace scope, not hidden prior-run state. |

## Validation Sign-Off

- [ ] All planned tasks have automated verification commands or explicit Wave 0 gaps
- [ ] Sampling continuity: no 3 consecutive tasks without automated verification
- [ ] Wave 0 covers chat rendering, run-action return shape, and hydrated-history behavior
- [ ] No watch-mode flags
- [ ] Feedback latency < 20s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
