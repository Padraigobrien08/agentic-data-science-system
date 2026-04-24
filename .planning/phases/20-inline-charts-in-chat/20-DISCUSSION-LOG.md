# Phase 20: Inline Charts in Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 20-Inline Charts in Chat
**Areas discussed:** Chart trigger policy, Chart spec source contract, Chart placement, Initial chart families, Caption and interaction depth

---

## Chart trigger policy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Show charts only when they materially strengthen the answer, capped at `1-2` per response | ✓ |
| B | Show a chart whenever structured chart data exists | |
| C | Let the frontend choose dynamically from density/width | |

**User's choice:** Option A.  
**Notes:** Charts should stay evidentiary, not decorative or routine.

---

## Chart spec source contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Backend emits explicit safe chart specs from trusted artifacts or metric outputs; frontend only renders | ✓ |
| B | Backend sends raw data slices and frontend decides chart types | |
| C | Hybrid backend family choice + frontend final series derivation | |

**User's choice:** Option A.  
**Notes:** The trust model stays deterministic only if chart meaning is decided server-side from trusted data.

---

## Chart placement in the answer

| Option | Description | Selected |
|--------|-------------|----------|
| A | Place charts inline beneath the prose answer and confidence header, but above the supplemental evidence disclosure | ✓ |
| B | Put charts inside the supplemental evidence disclosure | |
| C | Put charts in a desktop right rail | |

**User's choice:** Option A.  
**Notes:** The reading order remains answer first, visual proof second, deeper evidence third.

---

## Initial chart families

| Option | Description | Selected |
|--------|-------------|----------|
| A | Start with line charts for trends, grouped bar charts for peer comparisons, and simple explicit marker/timeline overlays | ✓ |
| B | Start with only line charts | |
| C | Include pie/donut/area charts from day one | |

**User's choice:** Option A.  
**Notes:** This matches the core EDGAR answer shapes without over-scoping the phase.

---

## Caption and interaction depth

| Option | Description | Selected |
|--------|-------------|----------|
| A | Give each chart one short caption plus lightweight hover tooltips only | ✓ |
| B | Add filters, metric switches, and expand/collapse controls immediately | |
| C | No captions, just show the chart | |

**User's choice:** Option A.  
**Notes:** Captioning is part of trust; chart controls would turn this into a broader BI feature.

---

## the agent's Discretion

- Exact “materially strengthens the answer” gating heuristic
- Exact chart card styling and responsive layout inside the current answer shell
- Exact tooltip behavior and caption wording

## Deferred Ideas

- User-controlled chart filters or metric switches
- Wider chart family expansion beyond the core initial set
- Chart pinning or reuse across follow-up messages
- Final narrative-and-chart responsive polish in Phase 21
