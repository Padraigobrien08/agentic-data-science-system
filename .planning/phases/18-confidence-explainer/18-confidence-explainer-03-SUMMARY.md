---
phase: 18-confidence-explainer
plan: 03
subsystem: ui
tags: [chat, narrative-answer, caveats, polish]
requires:
  - phase: 18-confidence-explainer
    provides: confidence pill and grouped disclosure
provides:
  - one short inline caution rider under the answer when needed
  - removal of redundant lower-page confidence/caveat chrome from the chat answer
  - hardened renderer tests for the narrative-first answer surface
affects: [18-confidence-explainer, chat-shell, narrative-answer]
tech-stack:
  added: []
  patterns:
    - keep caution inline and singular while reserving detail for the disclosure
    - remove repeated confidence/caveat sections from the answer body once the header pill exists
key-files:
  created: []
  modified:
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
    - frontend/src/components/runs/run-inspection-panel.test.tsx
key-decisions:
  - "The answer body should carry at most one short rider when caution is needed; the rest belongs in the explainer."
  - "Once confidence moved into the header, the old lower-page confidence/caveat block became redundant and was removed from the chat answer."
patterns-established:
  - "Narrative answer cards now use one caution line plus one explainer affordance rather than stacking multiple confidence treatments."
requirements-completed: []
duration: 7min
completed: 2026-04-24
---

# Phase 18 Plan 03 Summary

**The chat answer now shows one concise caution rider when needed and no longer repeats confidence/caveat chrome lower on the card.**

## Accomplishments

- Collapsed the inline caution behavior to one short rider sourced from the strongest available caveat.
- Removed the redundant lower-page confidence section from the chat answer so the header pill remains the single confidence entry point.
- Hardened the chat tests around the slimmer narrative-first answer surface.

## Task Commits

1. **Task 1: Collapse caveat chrome to one inline rider and remove redundant confidence sections** - `6d5e6fd`

## Next Phase Readiness

- The confidence layer is now compact enough to support the upcoming supplemental-evidence and chart work without overcrowding the answer body.
