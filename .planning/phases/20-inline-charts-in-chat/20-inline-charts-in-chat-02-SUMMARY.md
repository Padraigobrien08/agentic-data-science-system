---
phase: 20-inline-charts-in-chat
plan: 02
subsystem: frontend
tags: [charts, shadcn, recharts, chat, narrative-answer]
requires:
  - phase: 20-inline-charts-in-chat
    plan: 01
    provides: backend-owned inline chart preview contract and deterministic transparency payloads
provides:
  - local shadcn/Recharts chart surface for answer rendering
  - chat answer placement for inline visual evidence between prose and supplemental evidence
  - frontend chart view-model coverage and transcript regression protection
affects: [phase-20, chat-answer-rendering, structured-answer, frontend-build]
tech-stack:
  added:
    - recharts@^3.8.1
  patterns:
    - render-only chart consumption from backend-safe previews
    - centered answer-column chart placement above supporting-evidence disclosure
key-files:
  created:
    - frontend/src/components/ui/chart.tsx
    - frontend/src/components/structured-answer/inline-evidence-charts.tsx
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/app/globals.css
    - frontend/src/components/structured-answer/index.ts
    - frontend/src/components/structured-answer/types.ts
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/lib/__tests__/run-primary-view.test.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
    - frontend/src/components/runs/run-inspection-panel.test.tsx
key-decisions:
  - "Charts remain render-only in the frontend and consume bounded backend previews without inferring families or metric values."
  - "Visual evidence sits beneath the narrative answer and confidence header, and above the supporting-evidence disclosure."
  - "Wave 2 keeps charts capped to two vertically stacked cards instead of introducing dashboard-like layouts."
patterns-established:
  - "Local shadcn chart wrapper plus Recharts primitives for narrative-answer visual evidence."
  - "Transcript regression tests lock the prose -> visual proof -> supporting evidence order."
requirements-completed: []
duration: 30min
completed: 2026-04-24
---

# Phase 20 Plan 02: Inline Chart Renderer Summary

**Chat now renders backend-authored inline charts inside the answer column using a local shadcn/Recharts surface**

## Performance

- **Duration:** 30 min
- **Started:** 2026-04-24T22:25:30Z
- **Completed:** 2026-04-24T22:55:33Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added `recharts` plus a local shadcn-style chart wrapper so inline evidence charts can render inside the narrative answer surface.
- Added the dedicated `InlineEvidenceCharts` renderer and chart tokens in global CSS for line and grouped-bar previews.
- Verified that the answer builder and chat transcript continue to place visual evidence between the prose answer and the supplemental evidence disclosure.

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the shadcn/Recharts chart surface and answer-scoped renderer** — `23ec8fd`
2. **Task 2: Map safe chart previews into the answer view model and place charts inside chat** — `2bd5d35`

## Files Created/Modified

- `frontend/package.json` / `frontend/package-lock.json` — add the chart dependency used by the local wrapper.
- `frontend/src/app/globals.css` — add the chart color tokens used by the answer renderer.
- `frontend/src/components/ui/chart.tsx` — local shadcn-style chart scaffold for container and tooltip behavior.
- `frontend/src/components/structured-answer/inline-evidence-charts.tsx` — answer-scoped line/grouped-bar renderer with captions.
- `frontend/src/components/structured-answer/index.ts` / `types.ts` — export and type the chart surface.
- `frontend/src/lib/run-primary-view.ts` — map backend-safe chart previews into render-ready answer view data.
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — render visual evidence before the supporting-evidence disclosure.
- `frontend/src/lib/__tests__/run-primary-view.test.ts`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
- `frontend/src/components/runs/run-inspection-panel.test.tsx`

## Verification

- `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx`
  - `17 passed`
- `cd frontend && npm run build`
  - passed

## Issues Encountered

- The shadcn CLI stopped at an overwrite prompt for an existing component, so the chart wrapper was completed manually to stay within the plan’s owned file set.
- Recharts emits zero-size container warnings in jsdom tests; the tests still pass and the behavior can be hardened further in Wave 3 if needed.

## Next Phase Readiness

Wave 3 can now focus on strong-case gating, caption hardening, and fallback behavior because the renderer surface, transcript placement, and build/test gate are already in place.
