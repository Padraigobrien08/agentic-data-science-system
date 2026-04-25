---
phase: 21-narrative-answer-polish
plan: 01
subsystem: frontend
tags: [narrative-answer, hierarchy, spacing, citations, transcript]
requires:
  - phase: 17-narrative-answer-contract
    plan: 03
    provides: centered narrative-first answer shell
  - phase: 19-supplemental-evidence-disclosure
    plan: 03
    provides: supplemental evidence disclosure and secondary navigation
provides:
  - calmer editorial rhythm in the narrative answer shell
  - refined transcript width for the centered answer surface
  - quieter supporting-link styling beneath the answer
affects: [phase-21, chat-answer-rendering, transcript-layout]
tech-stack:
  added: []
  patterns:
    - narrative-first editorial answer hierarchy
    - centered chat reading column with calmer support chrome
key-files:
  created: []
  modified:
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/components/chat-shell/chat-message-list.tsx
    - frontend/src/components/structured-answer/supplemental-evidence-row.tsx
    - frontend/src/components/structured-answer/evidence-summary.tsx
key-decisions:
  - "The answer shell now reads more like one editorial reply and less like a stack of detached sections."
  - "Supporting proof links stay available, but their styling is quieter and more citation-like."
patterns-established:
  - "Prose-first answer hierarchy with subordinate support chrome."
requirements-completed: []
duration: 8min
completed: 2026-04-25
---

# Phase 21 Plan 01: Narrative Answer Shell Polish Summary

**The centered chat answer now reads more like one analyst reply and less like an assembled stack of UI blocks**

## Accomplishments

- Tightened the answer shell spacing, thesis width, and narrative section rhythm so the prose feels more intentional.
- Relaxed the transcript width and message framing so the centered answer uses space better without turning into a report page.
- Softened supplemental proof link styling so evidence still feels reachable but clearly secondary to the answer.

## Task Commit

1. **Task 1: Refine the answer shell into a calmer editorial reading surface** — `93a8f72`

## Verification

- `cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/lib/__tests__/run-primary-view.test.ts`
  - `16 passed`

## Next Readiness

Wave 1 is complete. The answer hierarchy is stable enough for the responsive composition and final chat/trace wording pass.
