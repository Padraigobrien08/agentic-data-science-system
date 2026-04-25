---
phase: 21
slug: narrative-answer-polish
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-25
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for final narrative-answer polish, responsive cleanup, and chat/trace wording alignment.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` |
| **Full suite command** | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx src/components/trace/run-trace-summary-view.test.tsx && npm run build` |
| **Estimated runtime** | ~20 seconds quick, ~45 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the narrowest frontend test slice that covers the touched answer/trace seam
- **After every plan wave:** Run the quick command above
- **Before milestone audit/archive:** Run the full suite and `npm run build`
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01 | 01 | 1 | ANSR-01, ANSR-03 | answer hierarchy + copy polish | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 21-02 | 02 | 2 | CONF-01, EVID-01, CHRT-01 | responsive layout + disclosure/chart composition | `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 21-03 | 03 | 3 | EVID-03, CHRT-03 | wording + navigation alignment + build | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx src/components/trace/run-trace-summary-view.test.tsx && npm run build` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

---

## Wave 0 Requirements

- [x] Reuse `frontend/src/components/chat-shell/chat-message-list.test.tsx` for centered answer-column and transcript hierarchy assertions
- [x] Reuse `frontend/src/components/chat-shell/chat-shell.test.tsx` for disclosure/chart/answer composition coverage
- [x] Reuse `frontend/src/lib/__tests__/run-primary-view.test.ts` for answer view-model expectations that should survive polish
- [x] Reuse `frontend/src/components/runs/run-inspection-panel.test.tsx` for secondary technical-surface behavior
- [x] Reuse `frontend/src/components/trace/run-trace-summary-view.test.tsx` for trace wording and navigation intent
- [x] Reuse existing `npm run build` gate to catch layout or component regressions

*Existing frontend test infrastructure covers all Phase 21 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Narrative answer feels like one editorial surface | ANSR-01, ANSR-03 | Requires visual judgment about rhythm, density, and hierarchy | 1. Open a completed narrative answer. 2. Confirm the prose reads as the dominant surface. 3. Confirm charts, disclosure, and pills feel subordinate. |
| Responsive answer remains calm across common viewport sizes | CONF-01, EVID-01, CHRT-01 | Requires real viewport inspection | 1. Inspect desktop, tablet, and narrow mobile widths. 2. Confirm the answer column stays centered or near-full-width with clean margins. 3. Confirm no side rail or overflow-heavy layout reappears. |
| Trace reads like a technical deep dive, not a second answer page | EVID-03, CHRT-03 | Requires product-language review | 1. Open trace from chat. 2. Confirm page labels and helper copy frame it as inspection/audit. 3. Confirm chat remains the primary reading surface. |

---

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers answer hierarchy, responsiveness, trace wording, and build safety
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
