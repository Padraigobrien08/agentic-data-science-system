---
phase: 12-runtime-reliability-for-chat-delivery
plan: 02
subsystem: chat
tags: [chat, health, runtime, ui]
requires:
  - phase: 12-01
    provides: "Worker boot and queue claim reliability in the documented stack"
provides:
  - "A public background-delivery health contract safe for workspace chat"
  - "Sync-first chat submission with explicit reroute disclosure"
  - "Workspace-level and per-message runtime truth in the chat shell"
affects: [backend, frontend, chat, health, tests]
tech-stack:
  added: []
  patterns: ["coarse public delivery status", "sync-first chat execution", "per-message delivery disclosure"]
key-files:
  created:
    - .planning/phases/12-runtime-reliability-for-chat-delivery/12-runtime-reliability-for-chat-delivery-02-SUMMARY.md
    - frontend/src/components/chat-shell/chat-composer.test.tsx
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.test.tsx
  modified:
    - backend/config/settings.py
    - backend/schemas/health.py
    - backend/api/routes/health.py
    - tests/test_backend_health.py
    - frontend/src/lib/api/types.ts
    - frontend/src/lib/api/runs.ts
    - frontend/src/app/projects/[projectId]/chat/page.tsx
    - frontend/src/actions/runs.ts
    - frontend/src/components/chat-shell/types.ts
    - frontend/src/components/chat-shell/chat-composer.tsx
    - frontend/src/components/chat-shell/chat-shell.tsx
    - frontend/src/components/chat-shell/chat-message-list.tsx
key-decisions:
  - "Workspace chat now forces synchronous execution even if a stale background-delivery field reaches the server action."
  - "Public `/v1/health` exposes only a coarse `background_delivery` posture, not ops-only worker internals."
  - "Runtime truth appears both near the composer and inside assistant messages so users are told what happened where they act and where they read."
patterns-established:
  - "Chat surfaces consume coarse public health slices while ops-only detail remains on protected routes."
  - "Server actions can coerce legacy delivery fields while still disclosing that reroute back to the user."
requirements-completed: [RUN-03]
completed: 2026-04-18
---

# Phase 12: Runtime Reliability for Chat Delivery Summary

**Sync-first chat runtime and public delivery-status contract**

## Accomplishments

- Added `background_delivery` to the public health contract so the chat page can distinguish `sync_only`, `background_ready`, and `background_degraded` without touching the ops-token worker endpoint.
- Changed workspace chat to create runs with `enqueue_execution: false` and execute them immediately, while still detecting legacy `enqueue_execution=on` submissions and marking them as rerouted.
- Removed the visible `Queue for worker` control from the composer, replaced it with a delivery-status strip, and carried the same runtime posture into pending and completed assistant messages.
- Added targeted backend and frontend regressions around the public health contract, sync-only composer state, and per-message reroute disclosure.

## Verification

- `python3 -m pytest tests/test_backend_health.py -q --tb=short`
- `cd frontend && npm run test -- src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/chat-shell/chat-message-list.test.tsx`

## Notes

- The chat action now always calls `executeRun(...)`, so the user-visible primary path is aligned with the runtime decision from Phase 12 discussion.
- The new delivery metadata is intentionally coarse: it tells the user whether chat is sync-only or degraded and whether a request was rerouted, without exposing worker-health internals on the public page.
