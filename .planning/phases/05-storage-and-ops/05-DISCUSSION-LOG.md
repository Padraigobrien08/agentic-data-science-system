# Phase 5: Storage and Ops - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-17
**Phase:** 05-Storage and Ops
**Areas discussed:** Degraded-state contract, Artifact ingest strategy, Retention policy scope, Retention execution model

---

## Degraded-state contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Make health and metrics surfaces report explicit degraded/error state when DB-backed queue reads fail instead of silently zero-filling | ✓ |
| B | Keep zero-fill behavior but add stronger logs | |
| C | Fail the routes outright without a degraded contract | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted operator-visible degraded-state reporting so dependency failures are not mistaken for an idle queue.

---

## Artifact ingest strategy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Use streamed copy/hash ingest into managed storage while keeping the current local object-store contract | ✓ |
| B | Keep full-memory reads for now and only document large-file limits | |
| C | Expand Phase 5 into a remote object-store rollout | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted the narrower streamed-ingest improvement instead of widening scope into a storage-backend migration.

---

## Retention policy scope

| Option | Description | Selected |
|--------|-------------|----------|
| A | Bound run history and raw model payload history first, while preserving a minimal audit trail and coupling blob cleanup to retained metadata | ✓ |
| B | Add aggressive artifact/blob deletion first and leave run/model history largely untouched | |
| C | Keep everything indefinitely and rely on manual database cleanup | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted retention focused on the highest-growth and most sensitive history, while preserving an auditable minimum record.

---

## Retention execution model

| Option | Description | Selected |
|--------|-------------|----------|
| A | Run retention as an explicit maintenance workflow/job with dry-run and reporting | ✓ |
| B | Delete records inline during normal request-path reads and writes | |
| C | Leave retention entirely manual and undocumented | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted an explicit maintenance path so retention stays observable, testable, and safer to operate in a brownfield system.

---

## the agent's Discretion

- Exact degraded-state schema and metrics encoding
- Exact streamed-ingest implementation details inside the storage abstraction
- Exact retention policy/config surface and audit-minimum record shape
- Exact maintenance invocation seam, scheduling guidance, and reporting format

## Deferred Ideas

None.
