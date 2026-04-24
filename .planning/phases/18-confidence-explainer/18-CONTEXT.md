# Phase 18: Confidence Explainer - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Move evidence-strength posture into the answer header as one compact, readable control that explains itself without dragging technical or repetitive caveat chrome into the main narrative flow.

This phase covers:

- the user-facing confidence label contract in the answer header
- the compact confidence pill and chevron affordance
- the safe backend rationale contract needed to explain the rating
- the policy for what caveat content stays inline versus what moves into the explainer

It does not redesign the evidence disclosure below the answer or add inline charts. Those remain Phase 19 and Phase 20 work.

</domain>

<decisions>
## Implementation Decisions

### Confidence label contract
- **D-01:** Keep backend storage and traceability on `high | medium | low | null`.
- **D-02:** Translate that internal scale into user-facing header labels: `Good | Medium | Bad | Not rated`.
- **D-03:** Phase 18 should preserve the existing critic/report semantics for system logic and auditing while presenting the friendlier product labels in chat.

### Header density
- **D-04:** The answer header should show one compact confidence pill only, for example `Evidence strength: Medium`, with the chevron built into that pill.
- **D-05:** Do not also expose `critic: success`, `report: success`, or similar technical status labels inline in the primary answer header.
- **D-06:** The confidence control should read like part of the answer surface, not like a subordinate technical strip.

### Explainer content shape
- **D-07:** The confidence explainer should be driven by a new safe backend rationale contract rather than loose frontend assembly from coarse caveat fields.
- **D-08:** That rationale contract should be grouped into 3 sections:
  - `what supports the rating`
  - `what weakens the rating`
  - `what data or coverage limits matter`
- **D-09:** The explainer must help the user understand why the rating is what it is without leaving chat.

### Inline caveat policy
- **D-10:** Keep only one short caveat rider under the answer when needed.
- **D-11:** Move the rest of the current caveat and badge bulk into the explainer instead of keeping a separate heavy caveat block inline.
- **D-12:** The inline answer should still feel grounded, but should no longer be visually dominated by redundant confidence chrome.

### the agent's Discretion
- Exact mapping presentation from backend `high/medium/low/null` to the user-facing semantic labels, as long as the product labels remain `Good | Medium | Bad | Not rated`
- Exact shadcn primitive choice for the explainer (`Popover`, `Dialog`, or `Sheet`) based on device and accessibility constraints
- Exact concise copy for the short inline caveat rider and the 3 explainer group headings

</decisions>

<specifics>
## Specific Ideas

- User wants `Evidence strength: Medium` in the top-right of the answer, visually aligned with the answer header rather than buried below it.
- User wants semantic status color: `Good` green, `Medium` yellow/amber, `Bad` red.
- User wants a chevron-triggered compact explainer that shows why the score is what it is, rather than a large permanent caveat block.
- The current raw technical labels and lower-page confidence strip are no longer aligned with the product direction.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — v1.3 milestone framing and the product shift toward narrative answers with explainable confidence posture
- `.planning/ROADMAP.md` — Phase 18 goal, plan breakdown, and explicit dependency from narrative answers toward evidence disclosure
- `.planning/REQUIREMENTS.md` — `CONF-01`, `CONF-02`, and `CONF-03`
- `.planning/STATE.md` — current project position after Phase 17

### Prior decisions that constrain this phase
- `.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md` — evidence is supplemental rather than the dominant reading mode
- `.planning/phases/16-secondary-run-inspection/16-CONTEXT.md` — trace remains the technical inspection surface, not the primary answer explanation
- `.planning/phases/17-narrative-answer-contract/17-CONTEXT.md` — the answer is now a centered narrative-first reading surface; confidence must integrate into that structure without recreating a summary-card feel

### Current confidence and transparency seams
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — current narrative-first answer surface that still needs header-level confidence treatment
- `frontend/src/components/structured-answer/confidence-strip.tsx` — current confidence UI still exposes raw technical status labels
- `frontend/src/components/structured-answer/caveat-badge-group.tsx` — current caveat explanation burden that should be collapsed
- `frontend/src/lib/run-primary-view.ts` — answer view builder that currently derives confidence, caveats, and narrative content together
- `frontend/src/components/structured-answer/types.ts` — typed frontend boundary for structured answer confidence and caveat state
- `backend/schemas/run_transparency.py` — current safe preview contract that lacks a deliberate explainer rationale model

### Backend rationale sources likely to feed the safe preview contract
- `backend/agents/output_schemas.py` — critic output schema with `overall_confidence`, `issues`, and trust-oriented fields
- `backend/agents/phase_outputs.py` — persisted agent phase output structures
- `backend/agents/traceability_summary.py` — existing backend summary shaping that may need to expose confidence rationale safely

### UI primitives and reusable surfaces
- `frontend/src/components/ui/` — current local shadcn surface; no existing `Popover`, `Dialog`, or `Sheet` primitive is installed yet
- `frontend/src/components/trace/trace-raw-detail-sheet.tsx` — example of existing disclosure-style interaction even though it is not a shadcn primitive

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatRunAnswerCard` already owns the narrative answer header, so it is the natural place to inline the new confidence pill.
- `run-primary-view.ts` already centralizes answer derivation and is the best seam for translating backend rationale into a compact frontend explainer model.
- Backend critic outputs already contain richer trust and issue information than the frontend currently sees, which means the main gap is the safe-preview contract rather than raw source availability.

### Established Patterns
- Chat is already the primary reading surface; confidence should explain the answer in place rather than pushing the user to trace.
- Current confidence UI is too technical and too visually heavy for the new narrative-first answer hierarchy.
- Current caveat UI spreads explanation across a strip plus badge groups; Phase 18 should consolidate that into one deliberate explainer surface.

### Integration Points
- The backend transparency schema will need new rationale fields that are safe to expose in chat.
- The frontend answer view builder will need a product-facing confidence model distinct from backend traceability enums.
- The chat renderer will need both a header pill and a responsive disclosure primitive, likely introducing a new shadcn component into `frontend/src/components/ui/`.

</code_context>

<deferred>
## Deferred Ideas

- Supplemental evidence disclosure below the answer with slim horizontal evidence cards — Phase 19
- Deterministic inline charts in chat using shadcn/Recharts — Phase 20
- Final responsive polish across the combined narrative/confidence/evidence surface — Phase 21

</deferred>

---

*Phase: 18-confidence-explainer*
*Context gathered: 2026-04-24*
