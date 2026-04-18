---
phase: 08-summary-first-large-trace-views
plan: 03
subsystem: frontend
tags: [trace, ui, raw-detail, regressions]
requires:
  - phase: 08-01
    provides: "Typed trace-summary route and bounded collection queries"
  - phase: 08-02
    provides: "Summary-first trace page and URL-backed collection navigation"
provides:
  - "One-at-a-time raw detail panels for selected steps and model calls"
  - "Legacy inspector links that point back into the summary-first trace surface"
  - "Focused regressions for bounded raw expansion and summary-first defaults"
affects: [frontend, trace-ui]
tech-stack:
  added: []
  patterns: ["item-scoped raw fetches", "one-open-at-a-time trace detail", "summary-first legacy inspector handoff"]
key-files:
  created:
    - frontend/src/components/runs/run-step-trace.test.tsx
    - frontend/src/components/trace/trace-raw-detail-sheet.tsx
  modified:
    - frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
    - frontend/src/components/runs/run-step-trace.tsx
    - frontend/src/components/trace/agentic-trace-view.tsx
    - frontend/src/components/trace/artifact-detail-panel.tsx
    - frontend/src/components/trace/run-trace-collection-panel.tsx
    - frontend/src/components/trace/run-trace-experience.tsx
    - frontend/src/components/trace/run-trace-summary-view.test.tsx
    - frontend/src/components/trace/run-trace-summary-view.tsx
    - frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx
    - frontend/src/components/transparency/model-call-summary-card.tsx
    - frontend/src/lib/api/types.ts
key-decisions:
  - "Raw payload fetches stay item-scoped and URL-driven rather than introducing a page-wide debug mode."
  - "Legacy step and model-call inspectors now route users back into the summary-first trace surface instead of rendering raw JSON inline by default."
  - "Artifact detail keeps the existing app-owned preview contract and only adds a trace link-back cue."
patterns-established:
  - "Privileged raw inspection belongs to a bounded side pane, not the default trace page payload."
  - "Legacy audit panels can remain available as long as they point back to the summary-first workflow for raw drill-down."
requirements-completed: [TRACE-02, TRACE-03]
duration: 11min
completed: 2026-04-18
---

# Phase 08: Summary-First Large Trace Views Summary

**Bounded raw-detail drill-downs, legacy inspector handoff, and focused regressions**

## Performance

- **Duration:** 11 min
- **Completed:** 2026-04-18T16:08:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments

- Added one-at-a-time raw detail loading for selected steps and model calls, with local error handling and close links that return the page to summary-first mode.
- Removed default inline step JSON from the legacy persisted-step inspector and replaced it with explicit links back into the summary-first trace route.
- Tightened model-call and summary-view regressions so bounded raw expansion is covered without bringing back first-load payload hydration.

## Task Commits

1. **Task 1-2: One-at-a-time raw detail surface and regressions** - pending commit

**Plan metadata:** pending summary commit

## Files Created/Modified

- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` - fetches a selected step or model call only when `focus=` is present
- `frontend/src/components/trace/run-trace-collection-panel.tsx` - renders the one-open-at-a-time raw detail surface for steps and model calls
- `frontend/src/components/trace/trace-raw-detail-sheet.tsx` - adds the bounded raw detail panel with local error handling
- `frontend/src/components/runs/run-step-trace.tsx` - removes default JSON panels and links users back to the summary-first trace view
- `frontend/src/components/transparency/model-call-summary-card.tsx` - keeps payloads bounded behind explicit raw affordances
- `frontend/src/components/trace/artifact-detail-panel.tsx` - adds a trace link-back cue while preserving app-owned artifact preview routing
- `frontend/src/components/runs/run-step-trace.test.tsx` - proves step JSON stays hidden by default

## Decisions Made

- Kept raw drill-down URL-driven so server-rendered trace pages remain shareable and no client-side debug state was introduced.
- Allowed the desktop and mobile raw-detail panels to share the same render path, even though jsdom will see both variants in tests.

## Deviations from Plan

- Reused the existing card surface for the bounded raw detail panel instead of introducing a new client-side Radix `Sheet` dependency in this wave.

## Issues Encountered

- The new tests needed to account for duplicate mobile and desktop raw-detail render paths in jsdom because responsive CSS classes do not hide DOM nodes during tests.

## User Setup Required

None.

## Next Phase Readiness

- Phase 08 now fully satisfies the large-trace browsing boundary: summary-first default, bounded collections, and item-scoped raw access.
- The next milestone work can move up a layer into evaluation control-plane persistence without revisiting large-trace loading behavior first.

## Self-Check

- `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short`
- `cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx`
- `cd frontend && npm run build`

---
*Phase: 08-summary-first-large-trace-views*
*Completed: 2026-04-18*
