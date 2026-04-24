---
phase: 20-inline-charts-in-chat
plan: 01
subsystem: api
tags: [charts, traceability, pandas, pydantic, typescript]
requires:
  - phase: 19-supplemental-evidence-disclosure
    provides: answer-first chat hierarchy and transparency-driven supplemental evidence seams
provides:
  - bounded inline chart preview models on run transparency
  - deterministic backend chart selection from trusted artifact CSVs
  - frontend wire types for render-only inline chart consumption
affects: [phase-20, chat-answer-rendering, run-transparency]
tech-stack:
  added: []
  patterns:
    - backend-owned inline chart eligibility and preview generation
    - fail-closed transparency parsing for malformed chart payloads
key-files:
  created:
    - backend/agents/inline_chart_preview.py
  modified:
    - backend/agents/traceability_summary.py
    - backend/schemas/run_transparency.py
    - frontend/src/lib/api/types.ts
    - tests/test_traceability_summary.py
    - tests/test_run_transparency_builders.py
    - tests/test_sprint3_transparency_api.py
key-decisions:
  - "Inline chart eligibility stays in backend traceability instead of frontend inference."
  - "Wave 1 ships only line and grouped_bar previews, capped to one deterministic preview per family."
  - "Malformed or weak chart inputs collapse to inline_charts=[] to preserve deterministic safety."
patterns-established:
  - "Backend-safe preview contract: semantic chart rows/series/markers instead of raw chart-library props."
  - "Artifact-backed chart gating: trend and peer previews require trusted CSV evidence before rendering."
requirements-completed: [CHRT-01, CHRT-02]
duration: 9min
completed: 2026-04-24
---

# Phase 20 Plan 01: Inline Chart Preview Contract Summary

**Deterministic line and grouped-bar chart previews sourced from trusted artifact CSVs and exposed through run transparency**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-24T22:25:04Z
- **Completed:** 2026-04-24T22:34:24Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Added a bounded `inline_charts` transparency contract with typed series, rows, markers, and artifact-role provenance.
- Built deterministic backend preview selection for one trend line chart and one peer grouped-bar chart from trusted artifact CSVs.
- Extended backend regression coverage so malformed payloads, weak artifact cases, and API transport all stay locked to the safe contract.

## Task Commits

Each task was committed atomically:

1. **Task 1: Define the safe inline chart preview contract on run transparency** - `afd3731` (test), `71a1991` (feat)
2. **Task 2: Build deterministic chart selection and persist backend-authored previews** - `142b292` (test), `aa42856` (feat)

**Plan metadata:** recorded in the final docs commit for this plan

_Note: This plan used TDD-style red/green commits for both tasks._

## Files Created/Modified
- `backend/agents/inline_chart_preview.py` - Builds deterministic line and grouped-bar preview payloads from trusted artifact CSVs.
- `backend/agents/traceability_summary.py` - Persists backend-authored `report.inline_charts` into the run traceability bundle.
- `backend/schemas/run_transparency.py` - Adds the bounded Pydantic inline chart models and fail-closed parser.
- `frontend/src/lib/api/types.ts` - Mirrors the backend inline chart contract for render-only frontend consumption.
- `tests/test_traceability_summary.py` - Covers preview selection, suppression, cap behavior, and traceability persistence.
- `tests/test_run_transparency_builders.py` - Covers safe inline chart parsing and malformed-data fallback.
- `tests/test_sprint3_transparency_api.py` - Locks the API transport shape for `transparency.inline_charts`.

## Decisions Made

- Inline chart selection runs entirely in the backend so the frontend never infers chart families or values from prose or raw payloads.
- Wave 1 limits previews to `line` and `grouped_bar`, with one candidate per family and a total cap of two charts.
- Invalid or underspecified chart payloads parse to `[]` rather than partially rendering speculative visuals.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The backend now exposes a stable `transparency.inline_charts` contract with deterministic captions, markers, and artifact provenance. Phase 20 plan 02 can consume that contract directly in chat without frontend-side chart inference.
