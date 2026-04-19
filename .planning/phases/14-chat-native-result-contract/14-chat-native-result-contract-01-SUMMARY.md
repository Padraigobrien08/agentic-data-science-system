---
phase: 14-chat-native-result-contract
plan: 01
subsystem: ui
tags: [react, nextjs, chat, structured-answer, server-actions]
requires: []
provides:
  - compact chat answer payload derived from the existing primary-answer builder
  - dedicated chat answer card and structured pending footprint
  - regression coverage for supported and unsupported assistant replies
affects: [14-chat-native-result-contract, 15-evidence-navigation-in-chat, chat-shell]
tech-stack:
  added: []
  patterns:
    - reuse run-page answer derivation for chat instead of inventing a parallel summary path
    - keep pending and completed assistant replies on one structured footprint
key-files:
  created:
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  modified:
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/actions/runs.ts
    - frontend/src/components/chat-shell/assistant-structured-frame.tsx
    - frontend/src/components/chat-shell/chat-message-list.tsx
    - frontend/src/components/chat-shell/types.ts
    - frontend/src/actions/runs.test.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
key-decisions:
  - "Chat replies now hydrate the finished run and derive their compact answer from the same primary-answer builder used on the standalone run page."
  - "Unsupported routing replies stay on the prose-and-rewrites branch; only supported runs render the structured answer card."
patterns-established:
  - "Compact chat answers are a projection of PrimaryAnswerView, not a new answer model."
  - "Pending assistant replies use the same conclusion-first footprint as completed replies."
requirements-completed: [CHAT-01]
duration: 15min
completed: 2026-04-19
---

# Phase 14 Plan 01 Summary

**Workspace chat now returns a compact structured answer card derived from persisted run output instead of plain prose plus link sprawl.**

## Performance

- **Duration:** 15 min
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments

- Added `CompactChatAnswerView` on top of the existing primary-answer builder so chat and run pages share one answer language.
- Updated the chat server action to hydrate completed runs and return structured answer payloads with run metadata.
- Replaced the placeholder assistant slot with a dedicated answer card and structured pending footprint.

## Task Commits

1. **Task 1: Add compact chat-answer view model and return it from the chat action** - `aefa041`
2. **Task 2: Render the compact answer card in chat and reuse the same footprint for pending replies** - `da1a236`

## Files Created/Modified

- `frontend/src/lib/run-primary-view.ts` - Added `CompactChatAnswerView` and the compact projection helper.
- `frontend/src/actions/runs.ts` - Hydrates the finished run and returns structured chat reply payloads.
- `frontend/src/components/chat-shell/types.ts` - Extends assistant messages with answer-card and run metadata fields.
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` - Renders the compact conclusion-first assistant card.
- `frontend/src/components/chat-shell/assistant-structured-frame.tsx` - Replaced placeholder copy with a pending structured footprint.
- `frontend/src/components/chat-shell/chat-message-list.tsx` - Routes supported replies into the answer card and pending frame.
- `frontend/src/actions/runs.test.ts` - Covers run hydration and answer-card payloads.
- `frontend/src/components/chat-shell/chat-message-list.test.tsx` - Covers structured completed and pending assistant rendering.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

None.

## User Setup Required

None.

## Next Phase Readiness

- Chat replies now carry the compact answer contract needed for persisted transcript hydration in Plan 02.
- The next plan can replace fake local sessions without changing the live reply shape again.
