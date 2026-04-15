# Phase 2: Worker Resilience - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-15
**Phase:** 02-worker-resilience
**Areas discussed:** Lease renewal strategy, expired-lease recovery behavior, retry visibility and operator truthfulness, cancellation during active execution

---

## Lease renewal strategy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Active heartbeat renewal while a worker owns the job | ✓ |
| B | Static lease only, just make it longer | |
| C | Renew only at explicit execution checkpoints | |

**User's choice:** A — Active heartbeat renewal while a worker owns the job
**Notes:** Accepted the recommended default.

---

## Expired-lease recovery behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A | Automatically requeue the same run after lease expiry, up to the attempt limit | ✓ |
| B | Mark the run `error` on first expired lease and require manual retry | |
| C | Auto-create a fresh retry path instead of reusing the same run | |

**User's choice:** A — Automatically requeue the same run after lease expiry, up to the attempt limit
**Notes:** Accepted the recommended default.

---

## Retry visibility and operator truthfulness

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep retries on the same run, but expose each attempt clearly in job/status history | ✓ |
| B | Keep retries mostly hidden; only show the latest state | |
| C | Surface retries as distinct attempt records/operators-first objects | |

**User's choice:** A — Keep retries on the same run, but expose each attempt clearly in job/status history
**Notes:** Accepted the recommended default.

---

## Cancellation during active execution

| Option | Description | Selected |
|--------|-------------|----------|
| A | Best-effort cancellation at explicit safe checkpoints; cancelled runs never auto-retry | ✓ |
| B | Treat cancellation as immediate hard-stop semantics | |
| C | Let the current attempt finish, then cancel before any retry | |

**User's choice:** A — Best-effort cancellation at explicit safe checkpoints; cancelled runs never auto-retry
**Notes:** Accepted the recommended default.

---

## the agent's Discretion

- Exact heartbeat cadence and renewal threshold
- Exact implementation seam for the renewal helper
- Exact status/API representation for attempt visibility, as long as retries remain explicit

## Deferred Ideas

None.
