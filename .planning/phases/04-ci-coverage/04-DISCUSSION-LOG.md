# Phase 4: CI Coverage - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 04-CI Coverage
**Areas discussed:** PR gate shape, CI auth posture, Frontend verification depth, Concurrency regression placement

---

## PR gate shape

| Option | Description | Selected |
|--------|-------------|----------|
| A | Add a dedicated PR-required full-stack integration job for `db + migrate + api + worker + web`, while keeping the current fast backend and frontend jobs | ✓ |
| B | Replace the current CI with one full-stack compose job | |
| C | Keep full-stack checks optional/nightly and only slightly widen current PR jobs | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted the split-gate approach so Phase 4 can validate the real documented stack without discarding the faster existing feedback loops.

---

## CI auth posture

| Option | Description | Selected |
|--------|-------------|----------|
| A | Make CI use the secure-default posture: bootstrap admin token for setup and ops token for `/metrics` and `/v1/worker/health` | ✓ |
| B | Loosen CI by enabling open registration and unauthenticated ops routes just for tests | |
| C | Skip auth-sensitive stack checks in PR CI | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted that CI should validate the real secure-default deployment path rather than introduce easier but misleading test-only security behavior.

---

## Frontend verification depth

| Option | Description | Selected |
|--------|-------------|----------|
| A | Add a narrow browser-level flow for authenticated login, run answer, trace navigation, and artifact download/proxy behavior | ✓ |
| B | Cover those flows with server-side integration tests around Next routes/actions only | |
| C | Keep frontend CI at Vitest + build only | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted browser-level coverage for the critical authenticated frontend path rather than relying only on unit tests or server-only integration seams.

---

## Concurrency regression placement

| Option | Description | Selected |
|--------|-------------|----------|
| A | Make focused collision, lease, and Postgres regressions PR-required as targeted test slices | ✓ |
| B | Run them only in the full-stack job | |
| C | Run them only on manual/nightly workflows | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted PR-required targeted regression slices so concurrency and lease failures are caught quickly and diagnosed clearly.

---

## the agent's Discretion

- Exact job/workflow split and naming
- Exact CI credential/env wiring for bootstrap and ops auth
- Exact browser-runner configuration and fixture mechanics
- Exact targeted regression subset promoted into PR-required slices

## Deferred Ideas

None.
