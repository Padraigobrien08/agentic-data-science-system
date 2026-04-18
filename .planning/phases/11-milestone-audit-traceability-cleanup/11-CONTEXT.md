# Phase 11: Milestone Audit Traceability Cleanup - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

This is a documentation and planning-traceability cleanup phase driven directly by the `v1.1` milestone audit. It exists to remove bookkeeping debt so milestone archival can trust automated requirement cross-checks and Nyquist validation status.

This phase covers:
- restoring truthful `requirements-completed` summary frontmatter in Phase 09 and Phase 10
- reconciling Phase 06 through Phase 10 `*-VALIDATION.md` files with the fact that those phases already executed and verified green
- refreshing `.planning/v1.1-MILESTONE-AUDIT.md` so it reflects the cleaned planning metadata

It does not reopen product behavior, add new runtime features, change the milestone scope, or broaden `v1.1` beyond the already verified deliverables in Phases 06 through 10.

</domain>

<decisions>
## Implementation Decisions

### Traceability scope
- **D-01:** Phase 11 is a gap-closure cleanup phase for planning artifacts only; it must not change runtime code or user-facing product behavior.
- **D-02:** The milestone audit file is the source of truth for what must be cleaned up in this phase.

### Summary requirement bookkeeping
- **D-03:** Phase 09 and Phase 10 summary frontmatter must explicitly list the requirement IDs their verification reports already satisfy.
- **D-04:** Summary body text should stay stable unless a wording adjustment is required to keep frontmatter and summary content truthful together.

### Nyquist bookkeeping
- **D-05:** Phase 06 through Phase 10 `*-VALIDATION.md` files must stop presenting stale planned or researched status once those phases have executed and verified successfully.
- **D-06:** Phase 11 should update validation bookkeeping to concrete executed state rather than inventing new validation coverage or rewriting acceptance criteria that were already verified.

### Audit refresh
- **D-07:** After the metadata cleanup lands, the milestone audit should be rerun and rewritten so the phase closes with a clean archival signal.
- **D-08:** This phase should treat a clean re-audit as the final proof that the bookkeeping debt is gone.

### the agent's Discretion
- Exact distribution of requirement IDs across the touched summary files, as long as the union is truthful and matches the verification evidence
- Exact wording for completed validation status and sign-off language, as long as it is explicit and no longer stale
- Exact wording of the refreshed audit narrative once the tech-debt items are removed

</decisions>

<specifics>
## Specific Ideas

- The audit found no unsatisfied product requirements, no broken integration seams, and no broken flows.
- The only open debt is planning metadata drift:
  - Phase 09 summary frontmatter omitted `VALID-01` and `EVAL-01`
  - Phase 10 summary frontmatter omitted `EVAL-02` and `OPS-01`
  - Phase 06 through 10 validation files still report planned or researched Nyquist bookkeeping
- The intended result is simple: Phase 11 should make `v1.1` ready to archive cleanly, not create a new milestone thread.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Audit and milestone scope
- `.planning/v1.1-MILESTONE-AUDIT.md` — exact debt items this phase must close
- `.planning/ROADMAP.md` — Phase 11 goal, dependencies, and success criteria
- `.planning/STATE.md` — current milestone position after adding the cleanup phase
- `.planning/PROJECT.md` — current milestone status and why archival is blocked
- `.planning/REQUIREMENTS.md` — requirement IDs that must stay unchanged while traceability is repaired

### Source-of-truth verification artifacts
- `.planning/phases/09-evaluation-control-plane/09-VERIFICATION.md` — verified requirement coverage for `VALID-01` and `EVAL-01`
- `.planning/phases/10-live-hybrid-execution-hardening/10-VERIFICATION.md` — verified requirement coverage for `EVAL-02` and `OPS-01`
- `.planning/phases/06-validation-boundaries-and-policy/06-VERIFICATION.md` — completed execution and verification state for Phase 06
- `.planning/phases/07-remote-artifact-storage-contract/07-VERIFICATION.md` — completed execution and verification state for Phase 07
- `.planning/phases/08-summary-first-large-trace-views/08-VERIFICATION.md` — completed execution and verification state for Phase 08

### Planning artifacts to reconcile
- `.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-01-SUMMARY.md`
- `.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-02-SUMMARY.md`
- `.planning/phases/09-evaluation-control-plane/09-evaluation-control-plane-03-SUMMARY.md`
- `.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-01-SUMMARY.md`
- `.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-02-SUMMARY.md`
- `.planning/phases/10-live-hybrid-execution-hardening/10-live-hybrid-execution-hardening-03-SUMMARY.md`
- `.planning/phases/06-validation-boundaries-and-policy/06-VALIDATION.md`
- `.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md`
- `.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md`
- `.planning/phases/09-evaluation-control-plane/09-VALIDATION.md`
- `.planning/phases/10-live-hybrid-execution-hardening/10-VALIDATION.md`

### Useful completed examples
- `.planning/phases/01-run-isolation/01-VALIDATION.md` — example of truthful validation sign-off with completed Wave 0 bookkeeping
- `.planning/phases/02-worker-resilience/02-VALIDATION.md` — example of completed validation status and green task map

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The milestone audit already names the exact files and debt items that must be closed.
- Phase 09 and Phase 10 verification reports already contain the truthful requirement coverage that summary frontmatter needs to mirror.
- Phase 01 and Phase 02 validation files show what completed Nyquist bookkeeping looks like in this repo.

### Established Patterns
- `requirements-completed` in summary frontmatter is used as one source in milestone requirement cross-checks.
- `*-VALIDATION.md` frontmatter and task tables are used to determine Nyquist compliance state in milestone audits.
- Milestone audits are stored in `.planning/v{version}-MILESTONE-AUDIT.md` and should be refreshed after cleanup instead of patched only in passing.

### Integration Points
- The union of summary frontmatter across all summary files in a phase must agree with that phase's `VERIFICATION.md` requirements table.
- The validation files must align with the phase verification reports so audit-time Nyquist discovery no longer marks those phases partial.
- The refreshed milestone audit must agree with the cleaned summary and validation docs, or Phase 11 has not actually closed its loop.

</code_context>

<deferred>
## Deferred Ideas

None. This phase should stay tightly scoped to the audit traceability debt already recorded.

</deferred>

---

*Phase: 11-milestone-audit-traceability-cleanup*
*Context gathered: 2026-04-18*
