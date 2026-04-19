# Phase 16: Secondary Run Inspection - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Reduce the standalone run page to a secondary inspection and verification surface now that the chat transcript carries the full answer, findings, caveats, and evidence navigation.

This phase covers the remaining duplication on the standalone run page:

- answer-summary copy that repeats what chat already shows
- full top-findings sections duplicated from chat
- confidence/caveat reading blocks duplicated from chat
- next-step link clusters that act like another primary answer footer

It does not remove deep inspection value from the run page. The run page should still support:

- status and lifecycle context
- verification entry points
- trace/deep-dive navigation
- execution and rerun controls where appropriate
- explicit navigation back to the chat thread

</domain>

<decisions>
## Implementation Decisions

### Page role
- **D-01:** The standalone run page should become a verification-first surface, not a second primary answer page.
- **D-02:** The page should explicitly direct users back to chat for primary reading rather than trying to outcompete the chat answer.

### Content reduction
- **D-03:** Remove or compress duplicated reading sections that Phase 15 already moved into chat: full top findings, confidence/caveats, and repeated next-step action stacks.
- **D-04:** Keep verification-oriented surfaces: run status banner, pipeline phase track, error summary, compact evidence/access strip, and deep-dive or rerun controls.

### Action hierarchy
- **D-05:** The strongest navigation on the run page should be `Back to chat` or equivalent answer-context return, with deep dive as a verification action rather than a competing primary reader.
- **D-06:** The run page should avoid multiple equal-weight CTA rows; actions should be compact and inspection-oriented.

### Reuse boundary
- **D-07:** Prefer trimming `RunPrimaryAnswer` into an inspection-oriented composition or replacing it with a smaller inspection component, not forking a third answer model.
- **D-08:** Keep all existing underlying answer derivation logic intact; this phase is presentation reduction, not semantics change.

### the agent's Discretion
- Exact balance between what remains on the run page versus what is linked outward to chat or trace
- Exact copy for the verification-first framing as long as it clearly points users back to chat for primary reading
- Exact component split between refactoring `RunPrimaryAnswer` and introducing a new inspection-specific component

</decisions>

<specifics>
## Specific Ideas

- Recommended direction selected autonomously:
  - move the run page header away from `Primary summary` framing
  - add an explicit return-to-chat affordance near the top
  - compress answer-reading sections into a short verification summary or remove them entirely
  - keep status, steps, error state, and verification links on the page
  - preserve deep dive and rerun affordances, but in a quieter inspection-oriented layout
- The likely highest-value seam is `RunPrimaryAnswer`: it still renders the same findings, evidence, confidence, and next-step sections that chat already owns after Phase 15.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md` — `NAV-03`
- `.planning/STATE.md`

### Prior decisions that constrain this phase
- `.planning/phases/14-chat-native-result-contract/14-CONTEXT.md`
- `.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md`
- `.planning/phases/15-evidence-navigation-in-chat/15-UI-SPEC.md`

### Current duplicated surfaces
- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`
- `frontend/src/components/runs/run-primary-answer.tsx`
- `frontend/src/components/runs/run-state-banner.tsx`
- `frontend/src/components/runs/verify-analysis-section.tsx`
- `frontend/src/components/structured-answer/*`

### Secondary/deep-dive surfaces that remain valid
- `frontend/src/app/projects/[projectId]/chat/page.tsx`
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RunStateBanner` and `RunPipelinePhaseTrack` already express inspection-oriented runtime state without duplicating the narrative answer.
- `VerifyAnalysisSection` already acts like a compact verification strip and is a likely keeper.
- The trace page already owns the true deep inspection workflow.

### Established Patterns
- Chat now carries the full answer and first-pass evidence navigation.
- The run page still presents itself as `Primary summary` and renders a broad reading stack, which is now the main duplication problem.
- Milestone trust still depends on explicit navigation and traceability, so Phase 16 should subtract duplication, not hide verification.

### Integration Points
- The run page likely needs a smaller inspection-specific body and updated header copy.
- `RunPrimaryAnswer` may either be reduced significantly or replaced on the run page with a verification-oriented component.
- Tests should focus on absence of duplicated reading blocks and presence of explicit return-to-chat navigation.

</code_context>

<deferred>
## Deferred Ideas

- Multi-run comparison or side-by-side inspection
- New trace visualizations or deep-dive redesign
- Fully message-anchored navigation from run page back to a specific chat answer

</deferred>

---

*Phase: 16-secondary-run-inspection*
*Context gathered: 2026-04-19*
