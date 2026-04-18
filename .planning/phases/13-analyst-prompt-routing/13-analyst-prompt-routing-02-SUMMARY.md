---
phase: 13-analyst-prompt-routing
plan: 02
subsystem: api
tags: [fastapi, routing, deterministic, pytest, prompt-preview]
requires:
  - phase: 12-runtime-reliability-for-chat-delivery
    provides: "A stable authenticated chat/backend baseline that Phase 13 can extend without changing run execution semantics"
provides:
  - "Structured deterministic planner guidance with rewrite suggestions and routing provenance"
  - "Additive POST /v1/runs/route-preview contract for pre-run routing previews"
  - "HTTP regression coverage for supported previews, unsupported scope guidance, and project ownership"
affects: [orchestration, backend, chat, tests]
tech-stack:
  added: []
  patterns: ["planner-owned routing guidance", "project-scoped route preview endpoint", "deterministic routing provenance surfaced at the API boundary"]
key-files:
  created:
    - .planning/phases/13-analyst-prompt-routing/13-analyst-prompt-routing-02-SUMMARY.md
    - backend/schemas/prompt_routing.py
    - tests/test_prompt_routing_api.py
  modified:
    - edgar_project/orchestration/schemas.py
    - edgar_project/orchestration/planner.py
    - backend/api/routes/runs.py
    - tests/orchestration/test_planner.py
key-decisions:
  - "Planner guidance stays on PlanningOutcome so preview callers return the exact deterministic routing result instead of re-deriving suggestions in the API layer."
  - "Route preview is additive and project-scoped, preserving existing POST /v1/runs and POST /v1/runs/{run_id}/execute semantics while letting chat stop unsupported prompts before run creation."
patterns-established:
  - "Unsupported deterministic planning returns rewrite_suggestions, effective_tickers, out_of_scope_tickers, and routing_source='deterministic'."
  - "Backend route previews use Planner() directly and serialize interpreted-goal fields only when deterministic routing succeeds."
requirements-completed: [PROMPT-03]
duration: 8 min
completed: 2026-04-18
---

# Phase 13 Plan 02: Analyst Prompt Routing Summary

**Deterministic planner guidance and a project-scoped route-preview API that stops unsupported prompts before failed run creation**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-18T22:40:13Z
- **Completed:** 2026-04-18T22:47:51Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments

- Extended `PlanningOutcome` so unsupported deterministic routing returns structured rewrite suggestions, scope guidance, effective tickers, and explicit `routing_source="deterministic"`.
- Added `POST /v1/runs/route-preview` with a typed backend contract that previews routing under project ownership without creating an `AnalysisRun`.
- Locked the new backend behavior with orchestration and API regressions for supported previews, unsupported out-of-scope prompts, and ownership failures.

## Task Commits

Each task was committed atomically through the TDD cycle:

1. **Task 1 RED: planner routing guidance tests** - `99b2879` (`test`)
2. **Task 1 GREEN: deterministic planner guidance** - `012b3db` (`feat`)
3. **Task 2 RED: route-preview API tests** - `c4be99f` (`test`)
4. **Task 2 GREEN: deterministic route-preview endpoint** - `6ce65ac` (`feat`)

## Files Created/Modified

- `edgar_project/orchestration/schemas.py` - Adds structured routing guidance fields to `PlanningOutcome`.
- `edgar_project/orchestration/planner.py` - Builds deterministic rewrite suggestions and carries scope-aware guidance into unsupported outcomes.
- `tests/orchestration/test_planner.py` - Verifies unsupported outputs include rewrite suggestions, provenance, and out-of-scope ticker guidance.
- `backend/schemas/prompt_routing.py` - Defines the typed request/response contract for deterministic route previews.
- `backend/api/routes/runs.py` - Adds the additive `POST /v1/runs/route-preview` endpoint and maps planner outcomes to the preview response.
- `tests/test_prompt_routing_api.py` - Covers supported previews, unsupported scope guidance, and project ownership at the HTTP boundary.

## Decisions Made

- Kept routing guidance on the planner outcome so the preview contract and future chat handling cannot drift from execution semantics.
- Added a separate preview route rather than changing create-run behavior, which preserves brownfield compatibility while still letting callers avoid failed run creation.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Chat can now preview unsupported routing deterministically before creating a run row, which gives Phase 13 plan 03 a stable backend seam to consume.
- The routing trust boundary is explicit at both planner and HTTP layers through `routing_source="deterministic"` and project-scoped preview enforcement.

## Self-Check: PENDING

---
*Phase: 13-analyst-prompt-routing*
*Completed: 2026-04-18*
