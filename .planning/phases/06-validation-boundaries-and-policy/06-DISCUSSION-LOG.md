# Phase 6: Validation Boundaries and Policy - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 06-Validation Boundaries and Policy
**Areas discussed:** Validation isolation policy, Degradation taxonomy, Live-use guardrails, Freshness semantics

---

## Validation isolation policy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep validation explicitly separate from normal user work at the policy layer, with distinct mode, visibility, and retention rules | ✓ |
| B | Mix validation into ordinary run surfaces and rely mostly on labels or tags to tell them apart | |
| C | Create a fully separate validation infrastructure in this phase instead of working through existing evaluation seams | |

**User's choice:** Proceed with recommended option; selected Option A.
**Notes:** User accepted that Phase 6 should lock a distinct validation policy without widening scope into a new execution/control-plane architecture yet.

---

## Degradation taxonomy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Distinguish at least `product_regression`, `upstream_sec_degraded`, `stale_source`, and `policy_skipped` | ✓ |
| B | Keep only coarse pass/fail/skipped/error states and rely on notes for interpretation | |
| C | Distinguish only SEC-vs-product and leave stale or policy cases implicit | |

**User's choice:** Proceed with recommended option; selected Option A.
**Notes:** User accepted a richer taxonomy so operators can route failures correctly instead of treating all non-pass outcomes as the same.

---

## Live-use guardrails

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep fixture and mocked evaluation as the default path; make `live` and `hybrid` explicit operator-invoked workflows that are non-merge-blocking and not ordinary user-run defaults | ✓ |
| B | Allow `live` and `hybrid` to become part of default CI or normal user workflows once implemented | |
| C | Make live validation the primary default validation mode and demote fixtures to fallback use only | |

**User's choice:** Proceed with recommended option; selected Option A.
**Notes:** User accepted conservative live-use guardrails so this phase protects product trust instead of chasing maximum automation immediately.

---

## Freshness semantics

| Option | Description | Selected |
|--------|-------------|----------|
| A | Judge `live` and `hybrid` on invariants and freshness windows; stale SEC data degrades rather than counting as product regression | ✓ |
| B | Compare live outputs against exact expected values or golden snapshots | |
| C | Leave freshness interpretation mostly manual and undocumented | |

**User's choice:** Proceed with recommended option; selected Option A.
**Notes:** User accepted invariant-based live semantics so SEC publication lag and drift do not create false product regressions.

---

## the agent's Discretion

- Exact schema and field names for validation mode, degradation classes, observation metadata, and policy flags
- Exact visibility/namespace mechanics so long as validation stays clearly distinct from normal user work
- Exact freshness-window and invariant defaults
- Exact way these policy decisions map onto existing `EvaluationRun` and benchmark manifests

## Deferred Ideas

- Dedicated validation UI — Phase 9
- Child `AnalysisRun` linkage — Phase 10
- Scheduled canaries with alerting — later milestone scope
