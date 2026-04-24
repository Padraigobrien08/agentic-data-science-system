# Phase 18: Confidence Explainer - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 18-Confidence Explainer
**Areas discussed:** Confidence label contract, Header density, Explainer content shape, Inline caveat policy

---

## Confidence label contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep backend `high | medium | low | null`, but translate the user-facing header badge to `Good | Medium | Bad | Not rated` | ✓ |
| B | Expose `high | medium | low | null` directly to the user | |
| C | Replace backend and frontend confidence vocabulary with a new shared scale | |

**User's choice:** Option A.
**Notes:** User wants the product-facing language to be `Good | Medium | Bad`, but there is no need to rewrite backend traceability semantics to get there.

---

## Header density

| Option | Description | Selected |
|--------|-------------|----------|
| A | Show one compact confidence pill only, with the chevron built in | ✓ |
| B | Keep the current pill plus inline `critic/report` status labels | |
| C | Keep confidence below the answer as a secondary section | |

**User's choice:** Option A.
**Notes:** The current strip is too technical and noisy for the narrative-first answer surface.

---

## Explainer content shape

| Option | Description | Selected |
|--------|-------------|----------|
| A | Use a new safe backend rationale contract with grouped sections for support, weaknesses, and data/coverage limits | ✓ |
| B | Derive the explainer entirely from existing frontend caveat fields | |
| C | Use a freeform explainer with no grouped structure | |

**User's choice:** Option A.
**Notes:** The user wants a compact explanation of why the evidence strength is what it is, not another loose pile of caveats or technical labels.

---

## Inline caveat policy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep one short rider under the answer when needed, and move the rest into the explainer | ✓ |
| B | Keep the current larger inline caveat block and also add the explainer | |
| C | Remove inline caveats completely and rely only on the explainer | |

**User's choice:** Option A.
**Notes:** The answer still needs a little grounding in-line, but the current caveat chrome is too heavy and redundant.

---

## the agent's Discretion

- Exact safe-preview rationale field names and grouping layout
- Exact shadcn disclosure primitive choice for desktop/mobile behavior
- Exact semantic color tokens and pill styling details for `Good`, `Medium`, `Bad`, and `Not rated`

## Deferred Ideas

- Supplemental evidence disclosure below the answer — Phase 19
- Inline charts in chat with shadcn/Recharts — Phase 20
- Final responsive narrative polish across the full answer surface — Phase 21
