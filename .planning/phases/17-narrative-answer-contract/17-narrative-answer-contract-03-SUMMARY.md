---
phase: 17-narrative-answer-contract
plan: 03
subsystem: frontend
tags: [nextjs, react, chat, narrative-answer, ui]
requires:
  - 17-narrative-answer-contract-02
provides:
  - centered narrative chat answer renderer
  - partial-answer limitation language inside the narrative shell
  - explicit error-state copy for failed runs
affects: [17-narrative-answer-contract, chat-answer, transcript-ui]
tech-stack:
  added: []
  patterns:
    - centered narrative reading column over subordinate support surfaces
    - explicit completed-state branching for success, partial, no-data, and error shells
key-files:
  created: []
  modified:
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
patterns-established:
  - "The assistant answer now renders as a single centered prose surface with support blocks below it instead of a dominant right rail."
requirements-completed: [ANSR-01, ANSR-02]
duration: 18min
completed: 2026-04-19
---

# Phase 17 Plan 03 Summary

**The Phase 17 renderer now treats the assistant response as one centered narrative reply, with support details visually subordinate and explicit partial/error copy in the same answer shell.**

## Performance

- **Duration:** 18 min
- **Started:** 2026-04-19T22:40:00Z
- **Completed:** 2026-04-19T22:58:00Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- Replaced the old two-column answer grid with one centered `max-w-[54rem]` narrative surface that renders the thesis and prose sections first.
- Moved findings, confidence, evidence, and orchestration detail into one muted support block beneath the prose body.
- Added explicit partial-answer limitation copy and the approved error-state language so failed or weak-support runs no longer look like vague placeholder cards.

## Task Commits

This wave lands in one feature commit because the renderer and its transcript-level tests had to move together.

1. **Tasks 1-2: Center the narrative answer renderer and harden partial/error shells** - `7e4e80e` (`feat`)

## Files Created/Modified

- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` - centered narrative answer shell with ordered prose sections and subordinate support surfaces.
- `frontend/src/components/chat-shell/chat-message-list.test.tsx` - regression coverage for narrative order, partial limitation copy, and explicit error copy.
- `frontend/src/components/chat-shell/chat-shell.test.tsx` - transcript-level regression that failed runs use the Phase 17 error shell.

## Decisions Made

- Kept the prose heading order deterministic through a small renderer-side ordering helper so section presentation is stable even if the preview arrives out of order.
- Left findings, confidence, and evidence in the card for compatibility, but demoted them into one lower-contrast support section below the answer body.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Build-time type narrowing was needed for the narrative section ordering helper**
- **Found during:** Task 2 verification
- **Issue:** The initial `Map`-based section ordering helper compiled in tests but failed the Next.js type-checking build because the narrative section headings are freeform strings, not a narrow literal union.
- **Fix:** Replaced the narrow `Map` lookup with a `Record<string, number>` built from the ordered headings list so arbitrary narrative headings remain sortable without a type error.
- **Files modified:** `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- **Verification:** `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build`
- **Committed in:** `7e4e80e`

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** No scope change; this was a type-safe implementation fix discovered during the required build gate.

## Issues Encountered

- One supporting sentence now appears twice in the primary answer test because the same fact is rendered once in the narrative body and once in the supporting-detail block. The test was updated to reflect the intended Phase 17 hierarchy instead of assuming single-use prose.

## User Setup Required

None.

## Next Phase Readiness

- Phase 17 now has the centered narrative shell required for later confidence-badge and supplemental-evidence work.
- Later phases can redesign confidence disclosure and evidence interaction without first undoing a right-rail answer layout.

---
*Phase: 17-narrative-answer-contract*
*Completed: 2026-04-19*
