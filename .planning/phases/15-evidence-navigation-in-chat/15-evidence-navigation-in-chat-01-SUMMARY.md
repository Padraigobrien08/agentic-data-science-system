---
phase: 15-evidence-navigation-in-chat
plan: 01
subsystem: ui
tags: [react, nextjs, chat, answer-contract, evidence]
requires:
  - phase: 14-chat-native-result-contract
    provides: persisted run-backed chat transcript and compact answer shell
provides:
  - richer chat answer-card contract derived from PrimaryAnswerView
  - live and hydrated history payloads with findings, confidence, caveats, and compact nav data
  - regression coverage for the richer answer payload in actions and history
affects: [15-evidence-navigation-in-chat, 16-secondary-run-inspection, chat-shell]
tech-stack:
  added: []
  patterns:
    - extend the existing chat answer contract instead of creating a parallel evidence model
    - hydrate artifact metadata for chat answers when evidence navigation depends on it
key-files:
  created: []
  modified:
    - frontend/src/lib/run-primary-view.ts
    - frontend/src/actions/runs.ts
    - frontend/src/lib/chat-run-history.ts
    - frontend/src/components/chat-shell/types.ts
    - frontend/src/actions/runs.test.ts
    - frontend/src/lib/chat-run-history.test.ts
key-decisions:
  - "Phase 15 answer data is still a projection of PrimaryAnswerView, not a new chat-only semantics layer."
  - "Live replies and hydrated history now carry the same richer answer-card contract."
patterns-established:
  - "Artifact metadata can be hydrated alongside the run when the chat surface needs richer evidence navigation."
  - "Phase 15 data work stays compatible with the Phase 14 one-thread transcript model."
requirements-completed: []
duration: 8min
completed: 2026-04-19
---

# Phase 15 Plan 01 Summary

**Chat replies and hydrated history now share one richer answer-card contract instead of the old summary-only payload.**

## Accomplishments

- Expanded the chat answer-card contract to include bounded findings, confidence, caveats, and compact navigation data.
- Updated both live chat replies and persisted run hydration to use the same richer answer builder.
- Added regression coverage to lock the richer answer payload on both seams.

## Task Commits

1. **Task 1: Extend the chat answer-card view model from the existing primary-answer derivation seam** - `cbb5479`
2. **Task 2: Return the richer answer-card contract from live chat replies and hydrated history** - `cbb5479`

## Next Phase Readiness

- The chat card now has the data it needs for inline findings, confidence/caveats, and compact evidence navigation.
- Phase 15 Plan 02 can stay focused on rendering density and navigation behavior rather than API or history shape.
