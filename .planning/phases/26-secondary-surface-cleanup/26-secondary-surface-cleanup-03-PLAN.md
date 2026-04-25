---
phase: 26-secondary-surface-cleanup
plan_id: 26-03
status: completed
requirements:
  - SURF-02
  - SURF-03
---

# Plan 26-03: Harden secondary-route return paths

## Goal

Make secondary surfaces reliably point back to the right conversation context.

## Work

- Keep chat as the explicit return target
- Preserve trace links as secondary navigation, not the primary shell
- Align user-facing route labels with the new IA
