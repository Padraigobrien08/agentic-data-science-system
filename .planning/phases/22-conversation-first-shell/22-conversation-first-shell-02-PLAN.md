---
phase: 22-conversation-first-shell
plan_id: 22-02
status: completed
requirements:
  - CONV-02
---

# Plan 22-02: Add new-chat affordance

## Goal

Let the user start a new chat from the shell without understanding a separate workspace setup step.

## Work

- Add a `New chat` action to the rail
- Reuse current scope as the starting point for the next chat
- Redirect directly into the new chat after creation
