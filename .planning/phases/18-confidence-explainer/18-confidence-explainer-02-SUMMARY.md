---
phase: 18-confidence-explainer
plan: 02
subsystem: frontend
tags: [react, nextjs, shadcn, popover, confidence, chat]
requires:
  - phase: 18-confidence-explainer
    provides: safe backend confidence-explainer preview
provides:
  - product-facing `Good | Medium | Bad | Not rated` confidence mapping
  - compact evidence-strength pill in the chat answer header
  - shadcn-style grouped confidence disclosure
affects: [18-confidence-explainer, chat-shell, structured-answer]
tech-stack:
  added:
    - "@radix-ui/react-popover"
  patterns:
    - keep confidence detail discoverable through compact disclosure instead of dedicated answer-body chrome
    - map coarse backend confidence semantics into product-facing labels at the view-model layer
key-files:
  created:
    - frontend/src/components/ui/popover.tsx
  modified:
    - frontend/package.json
    - frontend/package-lock.json
    - frontend/src/components/chat-shell/chat-run-answer-card.tsx
    - frontend/src/components/structured-answer/confidence-strip.tsx
    - frontend/src/components/structured-answer/types.ts
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/lib/__tests__/run-primary-view.test.ts
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
    - frontend/src/components/runs/run-inspection-panel.test.tsx
    - frontend/src/components/runs/run-primary-answer.tsx
key-decisions:
  - "Confidence is now expressed as one compact header pill instead of a separate lower-page technical strip."
  - "The disclosure renders grouped support, weaknesses, and coverage limits without exposing raw critic/report status labels."
patterns-established:
  - "Narrative answers now own the reading flow while confidence detail lives in a compact just-in-time disclosure."
  - "View-model mapping is the seam between coarse backend confidence values and product-facing label/tone choices."
requirements-completed: []
duration: 24min
completed: 2026-04-24
---

# Phase 18 Plan 02 Summary

**The answer header now carries one compact evidence-strength pill that opens a grouped explainer instead of pushing technical confidence detail into the body of the answer.**

## Accomplishments

- Added a shadcn-style popover primitive and used it to render the confidence explainer as a compact disclosure.
- Mapped backend `high | medium | low | null` values to the product labels `Good | Medium | Bad | Not rated`.
- Moved the confidence affordance into the narrative answer header and updated the tests for the new chat answer shape.

## Task Commits

1. **Task 1: Add the product-facing confidence pill and grouped explainer disclosure** - `6d5e6fd`

## Next Phase Readiness

- The answer header is now carrying confidence cleanly, so the remaining work is to keep only one short inline caution line and remove the leftover redundant caveat chrome from the answer surface.
