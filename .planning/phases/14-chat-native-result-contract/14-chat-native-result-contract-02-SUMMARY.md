---
phase: 14-chat-native-result-contract
plan: 02
subsystem: ui
tags: [react, nextjs, chat, persisted-history, runs]
requires:
  - phase: 14-chat-native-result-contract
    provides: compact chat answer payload and structured assistant message contract
provides:
  - persisted run-backed transcript seed for workspace chat
  - single-thread chat shell without fake local conversation tabs
  - recent-runs sidebar context tied to real run records
affects: [14-chat-native-result-contract, 15-evidence-navigation-in-chat, 16-secondary-run-inspection]
tech-stack:
  added: []
  patterns:
    - hydrate workspace chat from persisted runs on the server
    - keep one visible workspace thread and replace pending replies in place
key-files:
  created:
    - frontend/src/lib/chat-run-history.ts
    - frontend/src/lib/chat-run-history.test.ts
  modified:
    - frontend/src/app/projects/[projectId]/chat/page.tsx
    - frontend/src/components/chat-shell/chat-shell.tsx
    - frontend/src/components/chat-shell/chat-sidebar.tsx
    - frontend/src/components/chat-shell/types.ts
    - frontend/src/components/chat-shell/chat-shell.test.tsx
key-decisions:
  - "Workspace chat now rehydrates from persisted runs instead of client-only session stubs."
  - "The sidebar no longer pretends multiple conversations are durable; it shows recent real runs instead."
patterns-established:
  - "Each persisted run becomes one user message plus one assistant message in the visible transcript."
  - "New submissions append to the existing thread and reuse the same structured assistant reply shape."
requirements-completed: [CHAT-01, CHAT-03]
duration: 18min
completed: 2026-04-19
---

# Phase 14 Plan 02 Summary

**Workspace chat now reloads into a persisted run-backed transcript and continues as one visible thread instead of fake local conversations.**

## Performance

- **Duration:** 18 min
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Added a bounded persisted-run transcript builder that reuses the compact answer-card contract for hydrated history.
- Replaced the fake `local-1` conversation model with one workspace thread seeded from server-rendered history.
- Converted the sidebar into a read-only recent-runs rail tied to real run records.

## Task Commits

1. **Task 1: Build a persisted-run transcript mapper for the workspace chat seed** - `0627d8c`
2. **Task 2: Replace fake local sessions with one persisted workspace thread** - `f391c73`

## Files Created/Modified

- `frontend/src/lib/chat-run-history.ts` - Maps recent runs into transcript rows and sidebar metadata.
- `frontend/src/lib/chat-run-history.test.ts` - Verifies persisted runs become reload-safe chat history.
- `frontend/src/components/chat-shell/types.ts` - Replaced session stubs with a recent-run model.
- `frontend/src/app/projects/[projectId]/chat/page.tsx` - Seeds the chat shell from persisted run history.
- `frontend/src/components/chat-shell/chat-shell.tsx` - Maintains one visible thread and appends new requests in place.
- `frontend/src/components/chat-shell/chat-sidebar.tsx` - Shows recent real runs instead of fake conversation tabs.
- `frontend/src/components/chat-shell/chat-shell.test.tsx` - Verifies hydrated history stays visible when new prompts are sent.

## Deviations from Plan

None - plan executed as written.

## Issues Encountered

- The chat-shell test initially queried a goal string that now appears in multiple real UI locations; the assertion was tightened to allow the expected duplicates across transcript and recent-runs sidebar.

## User Setup Required

None.

## Next Phase Readiness

- The chat page now has reload-safe history, which gives the final Phase 14 run strip a stable surface to attach to.
- The remaining work is presentation cleanup: replace the legacy footer links with the compact `Open run` strip and harden the full frontend gate.
