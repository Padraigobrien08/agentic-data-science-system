---
phase: 08-summary-first-large-trace-views
plan: 02
subsystem: frontend
tags: [trace, ui, shadcn, ssr, navigation]
requires:
  - phase: 08-01
    provides: "Typed trace-summary route and bounded collection queries"
provides:
  - "SSR summary-first trace page built on the typed shell"
  - "URL-backed collection navigation for steps, artifacts, and model calls"
  - "Trace UI primitives and overview-first component tests"
affects: [frontend, trace-ui]
tech-stack:
  added: []
  patterns: ["summary-first SSR trace view", "URL-backed collection state", "shadcn-style trace primitives"]
key-files:
  created:
    - frontend/components.json
    - frontend/src/components/trace/run-trace-collection-panel.tsx
    - frontend/src/components/trace/run-trace-summary-view.tsx
    - frontend/src/components/trace/run-trace-summary-view.test.tsx
    - frontend/src/components/ui/badge.tsx
    - frontend/src/components/ui/button.tsx
    - frontend/src/components/ui/card.tsx
    - frontend/src/components/ui/input.tsx
    - frontend/src/components/ui/separator.tsx
    - frontend/src/components/ui/skeleton.tsx
    - frontend/src/lib/utils.ts
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/lib/api/runs.ts
    - frontend/src/lib/api/types.ts
    - frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
    - frontend/src/components/trace/agentic-trace-view.tsx
    - frontend/src/components/trace/deep-dive-layout.tsx
    - frontend/src/components/trace/run-trace-jump-nav.tsx
key-decisions:
  - "The trace route now fetches the typed shell first and only one active collection per request."
  - "Collection state lives in URL query params so the trace remains shareable and server-rendered."
  - "The dense legacy audit stack stays available behind a subordinate disclosure instead of being the first rendered surface."
patterns-established:
  - "Large-run trace views should open on overview and timeline, then one collection at a time."
  - "shadcn-style primitives can be used in the trace UI without coupling to the landing-page styling work."
requirements-completed: [TRACE-01, TRACE-02]
duration: 12min
completed: 2026-04-18
---

# Phase 08: Summary-First Large Trace Views Summary

**SSR summary-first trace page, URL-backed collection navigation, and restrained trace UI primitives**

## Performance

- **Duration:** 12 min
- **Completed:** 2026-04-18T14:55:52Z
- **Tasks:** 2
- **Files modified:** 19

## Accomplishments

- Rebuilt the trace route around `getRunTraceSummary(...)` and one active bounded collection instead of the old all-collections plus raw-payload first load.
- Added summary-first trace components for the overview, timeline preview, and collection panel.
- Introduced the trace-specific shadcn-style primitives needed for the new UI and locked the surface with focused component tests.

## Task Commits

1. **Task 1-2: Summary-first SSR trace page and collection UI** - `8463a1d` (`feat(08-02): add summary-first trace page`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` - switched the route to summary-first shell loading and URL-backed active collection state
- `frontend/src/lib/api/runs.ts` - added typed shell and query-aware collection helpers
- `frontend/src/lib/api/types.ts` - added the trace shell and collection query types
- `frontend/src/components/trace/run-trace-summary-view.tsx` - added the overview-first trace surface
- `frontend/src/components/trace/run-trace-collection-panel.tsx` - added the separate collection inspection panel
- `frontend/src/components/trace/agentic-trace-view.tsx` - moved the legacy audit stack below the summary-first surface
- `frontend/src/components/trace/run-trace-summary-view.test.tsx` - added overview/collection regression coverage

## Decisions Made

- Kept the legacy audit stack available but subordinate, rather than removing it during the summary-first migration.
- Reused URL query params as the source of truth for collection navigation instead of adding a client-side cache layer.

## Deviations from Plan

- `frontend/tailwind.config.ts` and `frontend/src/app/globals.css` were left untouched in this wave to avoid bundling unrelated landing-page theme work. The trace UI primitives use the existing CSS variables directly.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- The trace page now has a stable summary-first shell for item-scoped raw expansion in the next wave.
- Step, artifact, and model-call rows already carry explicit inspection actions and URL focus state, so the per-item detail surface can plug in without another routing change.

## Self-Check

- `cd frontend && npm run test -- run-trace-summary-view.test.tsx`
- `cd frontend && npm run build`

---
*Phase: 08-summary-first-large-trace-views*
*Completed: 2026-04-18*
