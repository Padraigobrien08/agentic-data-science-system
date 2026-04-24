---
phase: 20-inline-charts-in-chat
plan: 03
subsystem: api-frontend
tags: [charts, fallback, captions, gating, verification]
requires:
  - phase: 20-inline-charts-in-chat
    plan: 01
    provides: deterministic backend chart previews and transparency contract
  - phase: 20-inline-charts-in-chat
    plan: 02
    provides: inline chart renderer and answer-column placement
provides:
  - strong-case backend chart gating with deterministic captions
  - fallback-safe chart notice behavior in chat
  - full regression and production-build verification for Phase 20
affects: [phase-20, chat-answer-rendering, traceability, frontend-build]
tech-stack:
  added: []
  patterns:
    - fail-safe chart omission or notice rendering when previews cannot be trusted
    - backend-authored caption discipline for every surviving chart
key-files:
  created: []
  modified:
    - backend/agents/inline_chart_preview.py
    - tests/test_traceability_summary.py
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/components/structured-answer/inline-evidence-charts.tsx
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/lib/__tests__/run-primary-view.test.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
    - frontend/src/components/runs/run-inspection-panel.test.tsx
key-decisions:
  - "Unsupported or malformed previews now surface one explicit fallback notice instead of failing silently or crashing the chart section."
  - "Chart cards keep a fixed height so Recharts renders inside a stable answer-column slot."
  - "Strong-case gating stays backend-owned; the frontend only decides whether to render valid charts or the fallback notice."
patterns-established:
  - "Strong deterministic chart gating before chat rendering."
  - "Prose -> visual proof -> supplemental evidence remains stable even in fallback cases."
requirements-completed: [CHRT-03]
duration: 11min
completed: 2026-04-24
---

# Phase 20 Plan 03: Inline Chart Hardening Summary

**Inline charts now render only for strong deterministic cases, and weak or malformed previews degrade to one explicit fallback notice**

## Performance

- **Duration:** 11 min
- **Started:** 2026-04-24T22:55:40Z
- **Completed:** 2026-04-24T23:06:42Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Tightened backend chart gating so only strong trend or peer cases survive into `inline_charts`, each with a deterministic caption.
- Added frontend fallback behavior so dropped previews produce a slim `Chart preview unavailable...` notice instead of broken or empty chart chrome.
- Cleared the full Phase 20 regression and build gate across backend transparency, transcript rendering, and production build output.

## Task Commits

Each task was committed atomically:

1. **Task 1: Tighten strong-case gating and backend-authored caption generation** — `9816b96` (test), `5f792b9` (fix)
2. **Task 2: Add fallback-safe chart mapping and run the final regression/build gate** — captured in the final docs closeout commit for this plan

## Files Created/Modified

- `backend/agents/inline_chart_preview.py` — enforces stronger chart eligibility and caption generation.
- `tests/test_traceability_summary.py` — covers strong-case gating, peer suppression, and caption expectations.
- `frontend/src/lib/run-primary-view.ts` — adds `inlineChartNotice` and fail-safe chart mapping.
- `frontend/src/components/structured-answer/inline-evidence-charts.tsx` — renders either valid charts or one compact fallback notice.
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — preserves chart slot placement even when the fallback notice is shown.
- `frontend/src/lib/__tests__/run-primary-view.test.ts`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
- `frontend/src/components/runs/run-inspection-panel.test.tsx`

## Verification

- `python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short`
  - `24 passed`
- `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx`
  - `19 passed`
- `cd frontend && npm run build`
  - passed

## Issues Encountered

- Recharts still emits zero-size container warnings under jsdom even with a fixed chart height; the runtime behavior is correct and the warning remains non-blocking.

## Next Phase Readiness

Phase 20 is complete. Phase 21 can now focus on narrative-answer polish, responsive cleanup, and final wording/spacing refinement on top of a stable narrative + confidence + supplemental evidence + inline chart stack.
