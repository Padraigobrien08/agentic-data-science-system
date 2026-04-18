# Phase 8: Summary-First Large Trace Views - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 08-Summary-First Large Trace Views
**Areas discussed:** Opening trace shape, Collection navigation model, Raw expansion pattern, Default ordering and evidence linking

---

## Opening trace shape

| Option | Description | Selected |
|--------|-------------|----------|
| A | Open on a compact overview plus per-collection summary panels first, with heavier sections behind drill-down | ✓ |
| B | Keep the current all-sections deep-dive page as the default and only add more summary callouts above it | |
| C | Replace the current trace page with a single mixed inspector first and move the audit narrative behind a secondary tab | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted moving the default trace opening state to a bounded summary-first view rather than keeping the current dense audit stack as the first load.

---

## Collection navigation model

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep separate Steps, Artifacts, and Model calls collections, each with its own search/filter/pagination or jump controls | ✓ |
| B | Merge everything into one giant mixed event stream ordered by a shared timeline | |
| C | Keep the existing page-anchor sections only, with no real collection-level search/filter/pagination layer | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted a per-collection navigation model, which matches the existing backend resource split and avoids one oversized mixed stream.

---

## Raw expansion pattern

| Option | Description | Selected |
|--------|-------------|----------|
| A | Fetch privileged raw payloads on demand for one item at a time into inline drawers or detail panes | ✓ |
| B | Continue loading page-wide raw run/step/model payloads up front with `include_payloads=true` | |
| C | Remove inline raw inspection entirely and rely only on separate export/download flows | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted preserving raw access only as a privileged per-item drill-down instead of a default page-level fetch.

---

## Default ordering and evidence linking

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep the step timeline as the main spine and pin artifacts/model calls back to it with phase/role/status cues | ✓ |
| B | Reorder everything newest-first across all collections by default | |
| C | Make artifacts the primary browser and treat the execution timeline as secondary context | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted preserving the execution timeline as the organizing structure for trace understanding while linking other evidence collections back to it.

---

## the agent's Discretion

- Exact query shape and response model for summary-first trace APIs
- Exact filter/search/pagination UX per collection
- Exact inline detail treatment for privileged raw payload expansions
- Exact threshold for when large-run navigation modes become necessary

## Deferred Ideas

- Cross-run evidence-coverage summaries
- Dedicated evaluation-control-plane UI
- Signed/direct artifact delivery paths
