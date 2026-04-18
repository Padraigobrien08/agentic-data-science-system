# Phase 12: Runtime Reliability for Chat Delivery - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 12-Runtime Reliability for Chat Delivery
**Areas discussed:** Chat submission default, Worker-unavailable behavior, Degraded-state visibility in chat, Phase scope boundary

---

## Chat submission default

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep `Execute now` as the default chat path; keep queueing as an explicit secondary option | |
| B | Default chat to `Queue for worker`; keep `Execute now` as fallback | |
| C | Remove the choice and force synchronous execution for now | ✓ |

**User's choice:** Option C.
**Notes:** User wants runtime reliability ahead of preserving the async path as a first-class chat affordance.

---

## Worker-unavailable behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A | Disable or block `Queue for worker` when worker health is degraded, with a clear explanation and prompt to use `Execute now` | |
| B | Allow queueing anyway, but warn that delivery may be delayed or fail | |
| C | Silently fall back from queueing to synchronous execution | ✓ |

**User's choice:** Option C.
**Notes:** Recorded as automatic fallback without an extra confirmation step. Because the user also chose degraded-state visibility, fallback still needs to be disclosed in status/message UI rather than being completely invisible.

---

## Degraded-state visibility in chat

| Option | Description | Selected |
|--------|-------------|----------|
| A | Show both a workspace-level status near the composer and a per-message note when background delivery is degraded | ✓ |
| B | Show only the composer-level status | |
| C | Show only per-message degradation notices | |

**User's choice:** Option A.
**Notes:** This keeps chat aligned with the existing truthful-degraded-state posture established earlier in the project.

---

## Phase scope boundary

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep this phase limited to delivery-critical runtime seams only | |
| B | Also pull in the basic chat answer rendering contract now | |
| C | Expand to include auth/onboarding fixes discovered during testing | ✓ |

**User's choice:** Option C.
**Notes:** User wants the immediate testing blockers fixed together instead of splitting worker/runtime and first-run auth friction into separate early phases.

---

## the agent's Discretion

- Exact UI treatment for sync-default behavior and background-mode disclosure
- Exact implementation of automatic fallback while staying truthful
- Exact worker import-cycle/runtime repair
- Exact scope of onboarding fixes, as long as they are limited to first-run chat blockers

## Deferred Ideas

- Chat-native answer rendering contract — later phase
- Evidence navigation in chat — later phase
- Secondary run inspection redesign — later phase
