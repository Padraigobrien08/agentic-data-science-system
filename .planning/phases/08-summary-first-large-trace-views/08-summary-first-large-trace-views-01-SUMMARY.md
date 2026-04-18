---
phase: 08-summary-first-large-trace-views
plan: 01
subsystem: backend
tags: [trace, api, transparency, pagination, raw-access]
requires: []
provides:
  - "Typed trace-summary route for summary-first deep-dive opening"
  - "Bounded query support for steps, artifacts, and model calls"
  - "Admin-gated item-scoped raw step and model-call endpoints"
affects: [backend, api, trace-ui]
tech-stack:
  added: []
  patterns: ["typed trace shell", "bounded collection queries", "item-scoped privileged raw fetches"]
key-files:
  created:
    - tests/test_trace_summary_api.py
  modified:
    - backend/api/routes/runs.py
    - backend/schemas/api_phase_a.py
    - backend/repositories/run_step_repository.py
    - backend/repositories/model_call_repository.py
    - backend/repositories/artifact_repository.py
    - tests/test_sprint3_transparency_api.py
key-decisions:
  - "The first deep-dive load now comes from `/v1/runs/{id}/trace-summary` rather than `include_payloads=true` on the run route."
  - "Existing list routes kept their array response shape for compatibility, while gaining bounded query parameters for the new trace experience."
  - "Privileged raw access moved to one step or one model call at a time through dedicated item routes."
patterns-established:
  - "Large trace pages should open from typed summary contracts instead of raw payload blobs."
  - "Collection navigation can scale through route-level query params without breaking existing slim transparency consumers."
requirements-completed: [TRACE-01, TRACE-02, TRACE-03]
duration: 26min
completed: 2026-04-18
---

# Phase 08: Summary-First Large Trace Views Summary

**Backend trace-shell contract, bounded collection query support, and item-scoped raw fetch routes**

## Performance

- **Duration:** 26 min
- **Completed:** 2026-04-18T14:44:05Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added `/v1/runs/{id}/trace-summary` as a typed first-load contract with bounded previews for steps, artifacts, and model calls.
- Extended the existing collection routes with query parameters for filtering and pagination without breaking their slim array responses.
- Added per-item step and model-call endpoints so raw payload access is admin-gated and local to one item.

## Task Commits

1. **Task 1-2: Trace shell, bounded queries, and raw item routes** - `8b2b824` (`feat(08-01): add trace summary contract`)

**Plan metadata:** pending summary commit

## Files Created/Modified

- `backend/api/routes/runs.py` - added the trace-summary route, bounded collection query params, and item-scoped raw endpoints
- `backend/schemas/api_phase_a.py` - added typed trace-shell preview models
- `backend/repositories/run_step_repository.py` - added bounded step query support
- `backend/repositories/model_call_repository.py` - added bounded model-call query support
- `backend/repositories/artifact_repository.py` - added bounded artifact query support
- `tests/test_trace_summary_api.py` - added summary-first contract and raw-item access coverage
- `tests/test_sprint3_transparency_api.py` - added compatibility coverage for slim transparency under the new route/query behavior

## Decisions Made

- Preserved the existing `/steps`, `/artifacts`, and `/model-calls` response shapes for compatibility while still adding the query surface Phase 8 needs.
- Kept raw payload access off the trace shell entirely and restricted raw step or model-call access to item routes.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- The frontend can now rebuild the trace page on top of the typed shell without default `include_payloads=true` requests.
- Per-item raw drill-down work in the later wave can rely on dedicated step and model-call item routes instead of page-wide payload toggles.

## Self-Check

- `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short`

---
*Phase: 08-summary-first-large-trace-views*
*Completed: 2026-04-18*
