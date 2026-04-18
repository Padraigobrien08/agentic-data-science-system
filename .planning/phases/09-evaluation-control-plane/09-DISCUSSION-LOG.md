# Phase 9: Evaluation Control Plane - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 09-Evaluation Control Plane
**Areas discussed:** Operator entry surface, Supported suite contract, Evaluation ownership scope, Case review shape

---

## Operator entry surface

| Option | Description | Selected |
|--------|-------------|----------|
| A | Make the supported evaluation control plane API-backed first, while keeping the CLI as a compatibility path | ✓ |
| B | Keep the CLI and file outputs as the primary supported workflow, with API surfaces as later optional wrappers | |
| C | Build only a dedicated UI/operator console first and defer the underlying API contract | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted that supported evaluation workflows should become product resources instead of remaining CLI-first tooling.

---

## Supported suite contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Launch supported evaluations by curated suite IDs or approved manifests rather than arbitrary repo file paths | ✓ |
| B | Keep arbitrary `--suite path.json` style path selection as the supported operator contract | |
| C | Let users compose suites ad hoc from individual benchmark cases inside the control plane | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted stable, auditable suite identity as the supported contract instead of path-based invocation.

---

## Evaluation ownership scope

| Option | Description | Selected |
|--------|-------------|----------|
| A | Scope supported evaluation runs to projects by default, using the existing owner/project access model | ✓ |
| B | Make evaluation runs global operator records outside project ownership | |
| C | Keep ownership undefined for now and revisit once a UI exists | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted project-scoped evaluation history as the default boundary, matching the rest of the product’s access model.

---

## Case review shape

| Option | Description | Selected |
|--------|-------------|----------|
| A | Reopen evaluation runs as persisted run summaries plus explicit per-case results, rather than one opaque `results_json` blob | ✓ |
| B | Keep only suite-level summary and raw `results_json` blobs, with no first-class case-result resource | |
| C | Delay persisted case review and treat per-case detail as export-only for now | |

**User's choice:** All recommended options; selected Option A.
**Notes:** User accepted making case outcomes first-class persisted records so operators can reopen evaluation history meaningfully.

---

## the agent's Discretion

- Exact API route layout for evaluation-run create/list/detail behavior
- Exact persistence model for case results
- Exact CLI compatibility behavior
- Exact operator review surface beyond the minimum persisted API contract

## Deferred Ideas

- Child `AnalysisRun` linkage for live/hybrid validation
- Global cross-project evaluation console
- Arbitrary path-based suite execution as a supported product surface
