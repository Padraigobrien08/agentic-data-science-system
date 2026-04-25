# Phase 21: Narrative Answer Polish - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-25
**Phase:** 21-Narrative Answer Polish
**Mode:** Autonomous defaults from milestone direction and prior phase decisions
**Areas discussed:** Prose hierarchy, Responsive behavior, Chat/trace wording and navigation alignment

---

## Prose hierarchy

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep one centered narrative reading column, strengthen typography and spacing, and use lightweight inline source links only where they clarify specific claims | ✓ |
| B | Add more permanent support chrome back around the answer to make evidence more visible | |
| C | Expand the answer into a report-like multi-panel layout | |

**Autonomous choice:** Option A.  
**Notes:** The milestone direction is narrative-first. Phase 21 should finish that experience rather than re-fragment it.

---

## Responsive behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A | Preserve the same hierarchy on all screen sizes, but relax the centered column to near-full width with controlled margins on smaller screens | ✓ |
| B | Keep desktop spacing and density mostly unchanged on smaller screens | |
| C | Reintroduce side-rail behavior on larger screens to use width | |

**Autonomous choice:** Option A.  
**Notes:** This preserves the current answer model while avoiding cramped mobile/tablet behavior or split reading surfaces.

---

## Chat and trace relationship

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep chat as the answer-reading surface and trace as the technical deep dive, with wording and navigation adjusted to reinforce that distinction | ✓ |
| B | Let trace continue behaving like a quasi-answer page for power users | |
| C | Hide trace more aggressively in the chat experience | |

**Autonomous choice:** Option A.  
**Notes:** Trace is still useful, but Phase 21 should make its purpose unambiguous instead of letting it compete with chat.

---

## the agent's Discretion

- Exact typography and spacing tokens for the final narrative answer shell
- Exact inline citation/link treatment and copy
- Exact breakpoint behavior for charts, disclosure rows, and answer width
- Exact wording changes that make trace feel technical without making it feel hidden

## Deferred Ideas

- New answer semantics or answer-body expansion beyond the shipped Phase 17 contract
- New confidence semantics beyond the Phase 18 explainer contract
- New evidence structures beyond the Phase 19 disclosure contract
- New chart families or interactivity beyond the Phase 20 contract
