---
phase: 15-evidence-navigation-in-chat
plan: 02
subsystem: ui
tags: [react, nextjs, chat, findings, caveats, evidence-navigation]
requires:
  - phase: 15-evidence-navigation-in-chat
    provides: richer chat answer-card contract
provides:
  - inline findings and confidence/caveats inside the chat-native answer
  - one compact evidence-navigation area for report, evidence, artifacts, critic, and trace
  - chat-safe reuse of structured-answer primitives
affects: [15-evidence-navigation-in-chat, chat-shell, structured-answer]
tech-stack:
  added: []
  patterns:
    - reuse structured-answer primitives in a denser chat mode
    - keep evidence navigation centralized rather than repeated under every finding
key-files:
  created: []
  modified:
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/components/structured-answer/top-findings-list.tsx
    - frontend/src/components/structured-answer/finding-cards.tsx
    - frontend/src/components/structured-answer/caveat-badge-group.tsx
    - frontend/src/components/structured-answer/types.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
key-decisions:
  - "Inline findings, confidence, and caveats belong in chat now; the run page is no longer the primary answer-reading surface."
  - "Compact evidence navigation replaces scattered repeated evidence chips as the dominant navigation pattern."
patterns-established:
  - "The chat answer card can reuse the existing structured-answer seam with chat-specific density controls."
  - "One compact nav area is the default evidence entry point; item-level jumps are secondary."
requirements-completed: []
duration: 9min
completed: 2026-04-19
---

# Phase 15 Plan 02 Summary

**The chat-native answer is now a complete bounded reading surface with inline findings, confidence/caveats, and one compact evidence-navigation area.**

## Accomplishments

- Expanded `ChatRunAnswerCard` with `Top findings`, `Confidence & caveats`, and `Open evidence` sections.
- Reused the structured-answer primitives in a denser chat-safe mode instead of duplicating run-page UI logic.
- Added focused rendering tests to lock the richer chat answer card behavior.

## Task Commits

1. **Task 1: Expand the chat answer card with inline findings and bounded confidence/caveats** - `cbb5479`
2. **Task 2: Add one compact evidence-navigation area to the chat card** - `cbb5479`

## Next Phase Readiness

- The remaining gap is not missing answer content; it is quieter exact-jump behavior and final regression hardening.
- Phase 15 Plan 03 can finish by attaching secondary exact jumps without restoring the old chip clutter.
