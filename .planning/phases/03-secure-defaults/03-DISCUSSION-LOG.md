# Phase 3: Secure Defaults - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-16
**Phase:** 03-Secure Defaults
**Areas discussed:** Secret policy, Registration posture, Ops endpoint access, Raw payload visibility

---

## Secret policy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Fail startup if the built-in JWT secret is still active, except in tests or an explicit local-dev escape hatch | ✓ |
| B | Warn loudly but still start | |
| C | Fail only in production-like mode based on bind/env/profile heuristics | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted the strict startup-fail default with only an explicit local-development escape hatch.

---

## Registration posture

| Option | Description | Selected |
|--------|-------------|----------|
| A | Closed by default, with an explicit bootstrap path for the first/admin user | ✓ |
| B | Keep open registration by default, just document how to disable it | |
| C | Closed by default, no built-in bootstrap path | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted closed-by-default registration as long as operators still have an explicit bootstrap/admin path.

---

## Ops endpoint access

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep `/health` and `/ready` public, but require a dedicated ops credential for `/metrics` and `/v1/worker/health` | ✓ |
| B | Keep `/health` and `/ready` public, but require normal app bearer auth for `/metrics` and `/v1/worker/health` | |
| C | Leave `/metrics` and `/v1/worker/health` public and rely on network policy only | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted dedicated ops protection rather than normal user auth or network-only protection.

---

## Raw payload visibility

| Option | Description | Selected |
|--------|-------------|----------|
| A | Default to redacted/summary views; raw run/model payloads only in explicit debug or privileged ops mode, and stop persisting absolute filesystem paths | ✓ |
| B | Default to redacted views, but keep raw payload opt-in for any resource owner | |
| C | Remove raw payload API exposure entirely and only keep summaries | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted summary-first APIs, privileged/debug raw access, and removal of absolute path persistence from normal artifact metadata.

---

## the agent's Discretion

- Exact local-development escape-hatch config shape
- Exact bootstrap/admin mechanism
- Exact dedicated ops credential format/mechanism
- Exact redaction schema and privileged raw-access plumbing

## Deferred Ideas

None.
