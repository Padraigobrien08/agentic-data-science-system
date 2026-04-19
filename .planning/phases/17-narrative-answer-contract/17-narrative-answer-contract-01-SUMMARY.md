---
phase: 17-narrative-answer-contract
plan: 01
subsystem: api
tags: [fastapi, pydantic, transparency, llm, narrative-answer]
requires: []
provides:
  - backend-safe narrative answer preview on traceability and run transparency
  - report prompt/schema support for structured thesis and prose sections
  - regression coverage for full and partial narrative preview behavior
affects: [17-narrative-answer-contract, chat-answer, transparency, report-agent]
tech-stack:
  added: []
  patterns:
    - backend-authored narrative preview over the existing run-transparency seam
    - prompt/schema/version changes move together when report-agent output contracts tighten
key-files:
  created:
    - backend/agents/prompts/report/1.2.0.md
  modified:
    - backend/agents/output_schemas.py
    - backend/agents/phase_outputs.py
    - backend/agents/traceability_summary.py
    - backend/schemas/run_transparency.py
    - frontend/src/lib/api/types.ts
    - tests/test_run_transparency_builders.py
    - tests/test_sprint3_transparency_api.py
patterns-established:
  - "Narrative answer previews are authored on the backend and transported through `RunTransparencySummary` as safe typed data."
requirements-completed: [ANSR-01, ANSR-02]
duration: 18min
completed: 2026-04-19
---

# Phase 17 Plan 01 Summary

**Run transparency now carries a typed narrative answer preview sourced from report-agent output, with explicit partial fallback behavior when support is weak or unavailable.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-19T22:05:00Z
- **Completed:** 2026-04-19T22:23:24Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments

- Extended the report-agent contract so successful runs can author a thesis plus three bounded prose sections for chat-safe reuse.
- Added traceability-level synthesis for `full` and `partial` narrative answers, including explicit fallback reasons.
- Exposed the typed preview through the existing run-transparency API and mirrored it in the frontend wire types.

## Task Commits

Each task was committed atomically:

1. **Task 1: Extend report and traceability output to author a typed narrative preview** - `309f387` (`feat`)
2. **Task 2: Surface the narrative preview through run transparency and the frontend wire mirror** - `71d1f06` (`feat`)

## Files Created/Modified

- `backend/agents/output_schemas.py` - report-agent output now requires structured narrative prose fields.
- `backend/agents/phase_outputs.py` - report phase output persists a bounded `narrative_answer` object.
- `backend/agents/traceability_summary.py` - traceability now synthesizes `full` and `partial` narrative previews with fallback reasons.
- `backend/schemas/run_transparency.py` - run transparency parses and exposes the typed narrative preview.
- `frontend/src/lib/api/types.ts` - frontend wire mirror now includes the narrative preview interfaces.
- `backend/agents/prompts/report/1.2.0.md` - report prompt updated to request the new narrative fields.

## Decisions Made

- Kept the new answer contract on the existing `ai_agents.traceability -> RunTransparencySummary` seam rather than inventing a chat-specific API.
- Used explicit `mode` and `fallback_reason` fields so later frontend work can distinguish strong-support and limited-support answers without parsing prose.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Report prompt/version and regression fixtures had to move with the schema**
- **Found during:** Task 1 (Extend report and traceability output to author a typed narrative preview)
- **Issue:** Tightening `ReportAgentLLMOutput` would have broken live report generation and regression fixtures because the existing prompt and frozen report fixtures did not emit the new narrative fields.
- **Fix:** Added `backend/agents/prompts/report/1.2.0.md`, switched the default report prompt version, and updated the report regression anchors and stub pipeline fixtures to emit the structured narrative fields.
- **Files modified:** `backend/agents/prompts/report/1.2.0.md`, `backend/config/settings.py`, `tests/test_phase_outputs.py`, `tests/test_traceability_summary.py`, `tests/test_traceable_pipeline.py`, `tests/test_llm_output_quality_regression.py`, `tests/fixtures/llm_regression/report_with_evidence_anchors.json`
- **Verification:** `python3 -m pytest tests/test_run_transparency_builders.py -q --tb=short` and `python3 -m pytest tests/test_phase_outputs.py tests/test_traceability_summary.py tests/test_traceable_pipeline.py tests/test_llm_output_quality_regression.py -q --tb=short`
- **Committed in:** `309f387`

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** The deviation was necessary to keep the report-agent contract runnable and regression-safe. No scope creep beyond the backend answer seam.

## Issues Encountered

- Task 1 and Task 2 were slightly interdependent because the backend builder regression needed the transparency parser to understand `narrative_answer`. The parser was wired early so the wave could stay verifiable.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Wave 1 is complete and verified.
- The frontend can now migrate to `transparency.narrative_answer` in Wave 2 without reading raw payload JSON.

---
*Phase: 17-narrative-answer-contract*
*Completed: 2026-04-19*
