---
phase: 17-narrative-answer-contract
plan: 02
subsystem: frontend
tags: [nextjs, react, chat, narrative-answer, compatibility]
requires:
  - 17-narrative-answer-contract-01
provides:
  - narrative-first primary answer builder with explicit full, partial, and legacy modes
  - live chat replies and hydrated history that reuse the same narrative-first contract
  - compatibility coverage for summary-era runs without narrative previews
affects: [17-narrative-answer-contract, chat-answer, run-history, live-replies]
tech-stack:
  added: []
  patterns:
    - frontend consumes backend-authored narrative previews before legacy summary-era fields
    - narrative compatibility stays explicit through `mode` and `fallbackReason`
key-files:
  created: []
  modified:
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/actions/runs.ts
    - frontend/src/lib/chat-run-history.ts
    - frontend/src/lib/__tests__/run-primary-view.test.ts
    - frontend/src/actions/runs.test.ts
    - frontend/src/lib/chat-run-history.test.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
    - frontend/src/components/runs/run-inspection-panel.test.tsx
patterns-established:
  - "Frontend chat reply content now prefers `narrativeAnswer.thesis` and preserves `legacy` mode instead of centering `summaryLine`."
requirements-completed: [ANSR-01, ANSR-02]
duration: 16min
completed: 2026-04-19
---

# Phase 17 Plan 02 Summary

**The frontend answer builder, live reply path, and chat history now all treat the typed narrative preview as the primary answer contract, while older runs remain readable through an explicit `legacy` mode.**

## Performance

- **Duration:** 16 min
- **Started:** 2026-04-19T22:24:00Z
- **Completed:** 2026-04-19T22:40:00Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added a typed `NarrativeAnswerView` to the primary answer builder so the frontend can distinguish `full`, `partial`, and `legacy` answers without parsing prose.
- Migrated live chat replies and hydrated history to reuse `narrativeAnswer.thesis` instead of generic summary-era placeholders.
- Hardened the affected frontend tests so the new narrative contract is explicit anywhere `ChatAnswerCardView` or `PrimaryAnswerView` is mocked.

## Task Commits

This wave landed in one feature commit because `buildPrimaryAnswerView(...)` changed shape and its live-reply/history consumers had to move with it to keep the frontend type-safe and runnable.

1. **Tasks 1-2: Move the frontend answer builder, live reply path, and history hydration onto the narrative-first contract** - `4928e98` (`feat`)

## Files Created/Modified

- `frontend/src/lib/run-primary-view.ts` - answer derivation now exposes `NarrativeAnswerView` and prefers `transparency.narrative_answer`.
- `frontend/src/actions/runs.ts` - live chat replies now use the narrative thesis as the assistant message content.
- `frontend/src/lib/chat-run-history.ts` - persisted history now hydrates `narrativeAnswer` first and keeps `legacy` compatibility explicit.
- `frontend/src/lib/__tests__/run-primary-view.test.ts` - coverage for `full`, `partial`, and `legacy` answer modes.
- `frontend/src/actions/runs.test.ts` and `frontend/src/lib/chat-run-history.test.ts` - regression coverage for the live reply and history data paths.
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`, `frontend/src/components/chat-shell/chat-shell.test.tsx`, and `frontend/src/components/runs/run-inspection-panel.test.tsx` - typed mocks updated to reflect the required narrative answer contract.

## Decisions Made

- Kept `summaryLine` on the view model for migration compatibility, but demoted it behind `narrativeAnswer.thesis`.
- Preserved explicit `fallbackReason` values so later renderer work can distinguish limited-support and legacy-era answers without branching on raw strings.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Adjacent impact] Typed test doubles outside the core Wave 2 files needed the new narrative contract**
- **Found during:** Task 1 / Task 2 verification
- **Issue:** Once `narrativeAnswer` became required on the shared answer-card types, several adjacent component tests stopped type-checking even though their runtime assertions were still valid.
- **Fix:** Updated the affected test doubles in `chat-message-list.test.tsx`, `chat-shell.test.tsx`, and `run-inspection-panel.test.tsx` to carry explicit `narrativeAnswer` values aligned with the new compatibility modes.
- **Files modified:** `frontend/src/components/chat-shell/chat-message-list.test.tsx`, `frontend/src/components/chat-shell/chat-shell.test.tsx`, `frontend/src/components/runs/run-inspection-panel.test.tsx`
- **Verification:** `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/actions/runs.test.ts src/lib/chat-run-history.test.ts`
- **Committed in:** `4928e98`

---

**Total deviations:** 1 auto-fixed (non-blocking)
**Impact on plan:** No scope change; this kept the shared answer-card types coherent across the affected frontend tests.

## Issues Encountered

- The builder and its two chat data paths were more tightly coupled than the plan split implied because the narrative-first signature had to move across all call sites together.

## User Setup Required

None.

## Next Phase Readiness

- Wave 2 is complete and verified.
- The renderer can now assume every chat answer has an explicit `narrativeAnswer` with `full`, `partial`, or `legacy` mode for Wave 3 layout work.

---
*Phase: 17-narrative-answer-contract*
*Completed: 2026-04-19*
