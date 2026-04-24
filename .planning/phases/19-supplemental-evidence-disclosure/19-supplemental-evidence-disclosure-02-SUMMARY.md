---
phase: 19-supplemental-evidence-disclosure
plan: 02
subsystem: ui
tags: [chat, narrative-answer, disclosure, evidence]
requires:
  - phase: 19-supplemental-evidence-disclosure
    provides: merged supplemental evidence contract
provides:
  - collapsed-by-default supporting evidence disclosure
  - slim supplemental evidence row renderer with exact source jumps
  - explicit limited and empty evidence disclosure states in chat
affects: [19-supplemental-evidence-disclosure, chat-answer, transcript-ui]
tech-stack:
  added:
    - @radix-ui/react-collapsible
  patterns:
    - keep the narrative answer as the default reading path by collapsing support
    - render support as long, slim rows instead of stacked content-heavy cards
key-files:
  created:
    - frontend/src/components/ui/collapsible.tsx
    - frontend/src/components/structured-answer/supplemental-evidence-row.tsx
  modified:
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
    - frontend/package.json
    - frontend/package-lock.json
key-decisions:
  - "Supporting evidence stays collapsed by default even when support is strong."
  - "Thin or empty support still opens to explicit explanatory copy instead of disappearing."
patterns-established:
  - "The assistant answer now reveals proof on demand through one disclosure beneath the prose answer."
requirements-completed: [ANSR-03, EVID-01, EVID-02]
duration: 18min
completed: 2026-04-24
---

# Phase 19 Plan 02 Summary

**Supporting evidence is now hidden by default and opens into one slim merged proof layer only when the user asks for it.**

## Accomplishments

- Added a local shadcn-style collapsible primitive and a long, slim supplemental evidence row component with one exact `Open source` jump.
- Replaced the always-visible support panel in chat with a single `Show supporting evidence` disclosure beneath the narrative answer.
- Ensured weak-support and empty-support cases still render deliberate disclosure content instead of looking like a loading or rendering failure.

## Task Commits

This wave also landed in the shared Phase 19 feature commit because the new disclosure UI depended directly on the merged view-model work from Plan 01.

1. **Tasks 1-2: add the disclosure UI and slim support rows** - `f79537d`

## Next Phase Readiness

- The answer-first reading hierarchy now exists in chat.
- Phase 19 Plan 03 can finish the composition by keeping the navigation pills persistent but visually secondary below the disclosure.
