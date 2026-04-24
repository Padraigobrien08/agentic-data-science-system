# Phase 19: Supplemental Evidence Disclosure - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Make evidence clearly supplemental to the narrative answer by moving supporting material into a disclosure below the answer, while preserving exact jumps and compact secondary navigation.

This phase covers:

- the default collapsed/expanded behavior of the supplemental evidence disclosure
- the shape and density of the evidence rows inside that disclosure
- how current findings and alignment cards collapse into one unified supplemental evidence list
- where the `Report / Evidence / Artifacts / Critic / Trace` pills sit relative to the disclosure
- how thin-evidence or missing-evidence cases should still communicate that the system checked for support

It does not add charts or revisit the confidence pill/explainer contract. Those remain Phase 20 and completed Phase 18 work.

</domain>

<decisions>
## Implementation Decisions

### Disclosure behavior
- **D-01:** Supplemental evidence should be collapsed by default.
- **D-02:** The answer should expose one clear `Show supporting evidence` disclosure beneath the narrative answer instead of keeping evidence permanently open.
- **D-03:** Phase 19 should reinforce answer-first reading behavior, not just visually restyle the current support panel.

### Evidence card shape
- **D-04:** Evidence rows inside the disclosure should be long and slim, not tall stacked cards.
- **D-05:** Each evidence row should contain:
  - one short title
  - one sentence explaining why it matters
  - one exact jump link
- **D-06:** The disclosure should make better use of horizontal chat width than the current vertically stacked supporting cards.

### Disclosure contents
- **D-07:** Current takeaway rows and alignment/finding cards should merge into one unified supplemental evidence list.
- **D-08:** Phase 19 should remove the split between separate `Top findings` and `Finding cards` support sections on the chat answer path.
- **D-09:** The evidence disclosure should feel like one proof layer, not multiple mini-sections competing for attention.

### Secondary navigation placement
- **D-10:** Keep the `Report / Evidence / Artifacts / Critic / Trace` pills below the disclosure.
- **D-11:** Those pills should remain always visible but visually secondary to both the answer and the disclosure content.
- **D-12:** Phase 19 should not move the pills into the answer header or hide them inside the disclosure footer.

### Thin or missing evidence behavior
- **D-13:** The supplemental evidence disclosure should remain present even when evidence is weak or sparse.
- **D-14:** In thin-evidence cases, opening the disclosure should show a compact limited-evidence or empty-evidence state instead of disappearing entirely.
- **D-15:** The product should communicate “we checked, but support is limited,” not leave the user unsure whether evidence failed to load.

### the agent's Discretion
- Exact disclosure label copy and collapsed/expanded affordance styling
- Exact long-row evidence-card layout as long as it stays horizontally wide and vertically thin
- Exact tone and copy for the limited-evidence or empty-evidence state

</decisions>

<specifics>
## Specific Ideas

- User wants the answer to remain the center of the chat space, with evidence clearly subordinate.
- User wants evidence cards to be horizontally long and vertically thin.
- User wants the five secondary pills to remain available below the disclosure rather than competing with the answer header.
- User is explicitly comfortable with evidence being hidden by default as long as the disclosure still makes limited-support cases visible.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — v1.3 milestone framing after Phase 18
- `.planning/ROADMAP.md` — Phase 19 goal and success criteria
- `.planning/REQUIREMENTS.md` — `ANSR-03`, `EVID-01`, `EVID-02`, and `EVID-03`
- `.planning/STATE.md` — current project position after Phase 18

### Prior decisions that constrain this phase
- `.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md` — evidence belongs in chat, but is meant to be secondary rather than dominant
- `.planning/phases/17-narrative-answer-contract/17-CONTEXT.md` — the answer is a narrative-first reading surface, not a summary-card shell
- `.planning/phases/18-confidence-explainer/18-CONTEXT.md` — confidence is already handled at the header level and should not be re-expanded into the support area

### Current answer and evidence surfaces
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — current narrative-first answer with always-visible support section
- `frontend/src/components/structured-answer/top-findings-list.tsx` — current takeaway row renderer
- `frontend/src/components/structured-answer/finding-cards.tsx` — current alignment/finding card renderer
- `frontend/src/components/structured-answer/evidence-summary.tsx` — current secondary evidence-navigation block
- `frontend/src/lib/run-primary-view.ts` — source of takeaway rows, alignment findings, evidence links, and provenance hints
- `frontend/src/components/chat-shell/chat-message-list.tsx` — centered transcript layout that constrains the answer/disclosure width

### Secondary surfaces that remain linked, not inlined fully
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- `frontend/src/app/artifacts/[artifactId]/page.tsx`
- `frontend/src/components/transparency/report-evidence-panel.tsx`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatRunAnswerCard` already has a clear narrative-first shell and a bounded lower support area, so Phase 19 is primarily a disclosure and information-architecture change, not a full answer rewrite.
- `TopFindingsList` and `FindingCards` already isolate the two current support shapes, which makes them the natural candidates either to merge or to replace with a slimmer shared evidence-row component.
- `EvidenceSummary` already owns the five secondary pills and provenance hint, so Phase 19 can reposition or restyle that surface instead of rebuilding the escape-hatch navigation model from scratch.
- `run-primary-view.ts` already centralizes takeaways, alignment findings, evidence links, and provenance hints, so the disclosure should still derive from that single view-model seam.

### Established Patterns
- The answer now owns the top of the card and confidence already lives in the header, so the support area should keep shrinking rather than re-expanding.
- The current `Supporting detail` section is still always visible whenever findings exist, which conflicts with the new answer-first reading hierarchy.
- The current support layer is fragmented into takeaway rows, alignment cards, and pills, which is exactly the architecture this phase is meant to simplify.

### Integration Points
- Phase 19 will likely need a new disclosure wrapper inside `ChatRunAnswerCard` plus a new shared slim evidence-row component or a substantial refactor of the existing findings renderers.
- `run-primary-view.ts` will likely need a unified supplemental-evidence view instead of separate `takeawayRows` and `alignmentFindings` being rendered as separate blocks.
- The pills can remain sourced from current `navigationItems`, but their placement and visual weight should shift to the bottom of the support area.

</code_context>

<deferred>
## Deferred Ideas

- Deterministic inline charts in chat using shadcn/Recharts — Phase 20
- Final narrative/evidence/citation polish across screen sizes — Phase 21
- Persisting disclosure open/closed state per workspace or per user

</deferred>

---

*Phase: 19-supplemental-evidence-disclosure*
*Context gathered: 2026-04-24*
