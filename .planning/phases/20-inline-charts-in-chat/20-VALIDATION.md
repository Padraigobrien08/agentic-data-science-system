---
phase: 20
slug: inline-charts-in-chat
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-24
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for deterministic inline chart previews, shadcn/Recharts rendering, and strict chart-gating behavior in the chat answer.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | `pytest` + `vitest` |
| **Config file** | `frontend/vitest.config.ts` |
| **Quick run command** | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx` |
| **Full suite command** | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx && npm run build` |
| **Estimated runtime** | ~20 seconds quick, ~45 seconds full |

---

## Sampling Rate

- **After every task commit:** Run the tightest backend or frontend command for the seam that changed
- **After every plan wave:** Run the quick command above
- **Before `$gsd-verify-work`:** Full suite and `npm run build` must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01 | 01 | 1 | CHRT-01, CHRT-02 | backend contract | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short` | ⚠️ extend existing | ⬜ pending |
| 20-02 | 02 | 2 | CHRT-01, CHRT-03 | renderer + view model | `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` | ⚠️ extend existing | ⬜ pending |
| 20-03 | 03 | 3 | CHRT-01, CHRT-02, CHRT-03 | gating + build | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx && npm run build` | ⚠️ extend existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ extend existing coverage*

---

## Wave 0 Requirements

- [x] Extend `tests/test_traceability_summary.py` — deterministic chart-preview selection and bounded contract behavior
- [x] Extend `tests/test_run_transparency_builders.py` — `inline_charts` parsing/serialization in the safe transparency surface
- [x] Extend `tests/test_sprint3_transparency_api.py` — chart-preview exposure through the run detail API
- [x] Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` — chart-view derivation defaults to `[]` and maps bounded previews
- [x] Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` — inline chart placement between prose and supplemental evidence
- [x] Extend `frontend/src/components/chat-shell/chat-shell.test.tsx` — hydrated history renders charts with the same hierarchy
- [x] Reuse existing build gate — chart components and shadcn chart wrapper must pass `npm run build`

*Existing backend and frontend test infrastructure covers all Phase 20 requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Charts feel like visual proof, not a dashboard | CHRT-01 | Requires visual judgment about answer hierarchy and chart emphasis | 1. Open a completed answer with charts. 2. Confirm prose remains the dominant reading surface. 3. Confirm charts sit between the prose block and supplemental evidence disclosure without overwhelming the answer. |
| Captions clearly explain what each chart shows and why it matters | CHRT-03 | Requires product-language review rather than structural assertion only | 1. Open a charted answer. 2. Confirm each chart has a short caption. 3. Confirm the caption explains both the metric/trend and why it matters to the answer. |
| Tooltips remain lightweight and charts do not expose exploratory controls | CHRT-01, CHRT-03 | Requires interaction review in a real browser | 1. Hover each chart. 2. Confirm lightweight tooltip behavior works. 3. Confirm there are no filters, metric toggles, or BI-style controls introduced by the chart surface. |

---

## Validation Sign-Off

- [x] All planned tasks have automated verification commands or explicit Wave 0 coverage
- [x] Sampling continuity: no 3 consecutive tasks without automated verification
- [x] Wave 0 covers backend chart contract, frontend chart mapping, renderer hierarchy, and build safety
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
