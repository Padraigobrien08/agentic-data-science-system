# Phase 21: Narrative Answer Polish - Context

**Gathered:** 2026-04-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Refine the end-to-end narrative answer experience so the shipped `v1.3` answer stack feels deliberate, readable, and consistent across desktop and smaller viewports.

This phase covers:

- final prose hierarchy, spacing, and citation/link polish for the narrative answer
- responsive tuning for the centered answer column, inline charts, confidence pill, and supplemental evidence disclosure
- final chat/trace wording and navigation alignment so trace remains the technical deep-dive surface

It does not reopen the narrative answer contract, confidence explainer contract, evidence disclosure contract, or chart-selection contract that were already locked in Phases 17-20.

</domain>

<decisions>
## Implementation Decisions

### Prose hierarchy and link polish
- **D-01:** Keep the answer as one centered reading column with the prose body as the clear primary surface.
- **D-02:** Strengthen typography, section rhythm, and vertical spacing so the answer reads like a polished analyst memo rather than a stack of assembled UI blocks.
- **D-03:** Use lightweight inline source/citation links only where they clarify a specific claim; do not turn the answer into a footnote-heavy report.

### Responsive behavior
- **D-04:** Preserve the answer-first hierarchy on all screen sizes: narrative answer, confidence posture, optional charts, supplemental evidence disclosure, then secondary pills.
- **D-05:** On smaller screens, the centered answer should relax toward a near-full-width reading column with controlled margins rather than preserving desktop spacing mechanically.
- **D-06:** Disclosure, chart, and supporting-evidence surfaces should adapt responsively without reintroducing side rails, overflow-heavy layouts, or competing reading regions.

### Chat and trace relationship
- **D-07:** Chat remains the primary reading surface for the answer.
- **D-08:** Trace remains the technical inspection surface and should be described consistently as the deep-dive or technical surface, not as another primary answer page.
- **D-09:** Final wording and navigation should reduce ambiguity about when to stay in chat versus when to open trace.

### Polish scope
- **D-10:** Phase 21 should focus on coherence and finish quality across the already-shipped answer architecture, not reopen feature scope from earlier phases.
- **D-11:** The final milestone should ship as one intentional narrative-first answer experience rather than a visible sequence of incremental UI layers.

### the agent's Discretion
- Exact typography, spacing, and container refinements, as long as the answer stays centered and clearly primary.
- Exact inline-link treatment and citation-copy style, as long as links stay lightweight and non-disruptive.
- Exact mobile/tablet responsive breakpoints and disclosure/chart stacking behavior, as long as the answer hierarchy remains intact.
- Exact wording adjustments for chat and trace navigation labels, helper copy, and empty states.

</decisions>

<specifics>
## Specific Ideas

- The user wants the answer to feel more like ChatGPT’s centered reading surface: read the answer in the middle, then inspect supporting material below it.
- The user wants width used better for the answer itself, not wasted on redundant chrome or fragmented support panels.
- The user wants trace to remain available, but no longer behave like a competing answer-reading page.
- The user described this phase as worthy of its own milestone finish step, which means polish quality matters as much as raw functionality here.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — current `v1.3` milestone framing after inline charts
- `.planning/ROADMAP.md` — Phase 21 goal and remaining plan outline
- `.planning/REQUIREMENTS.md` — `v1.3` answer, confidence, evidence, and chart requirements that this polish pass must preserve
- `.planning/STATE.md` — current project position after Phase 20

### Prior decisions that constrain this phase
- `.planning/phases/17-narrative-answer-contract/17-CONTEXT.md` — narrative answer is the primary product surface and uses analyst-memo voice
- `.planning/phases/18-confidence-explainer/18-CONTEXT.md` — confidence lives in a compact header pill with a small explainer, not a large inline block
- `.planning/phases/19-supplemental-evidence-disclosure/19-CONTEXT.md` — evidence is supplemental, collapsed by default, and remains secondary to the answer
- `.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md` — charts are deterministic inline visual proof, capped, and subordinate to the answer

### Current answer and navigation seams
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — primary answer composition and the main polish target
- `frontend/src/components/chat-shell/chat-message-list.tsx` — centered conversation layout and message width behavior
- `frontend/src/components/structured-answer/inline-evidence-charts.tsx` — inline chart surface that needs final responsive polish
- `frontend/src/components/structured-answer/supplemental-evidence-disclosure.tsx` — disclosure behavior and secondary proof layer
- `frontend/src/components/structured-answer/evidence-strength-pill.tsx` and `frontend/src/components/structured-answer/confidence-explainer-popover.tsx` — confidence header posture and disclosure copy
- `frontend/src/components/trace/run-trace-summary-view.tsx` and `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` — trace wording and technical-surface alignment
- `frontend/src/lib/run-primary-view.ts` — answer view-model seams for narrative sections, charts, evidence disclosure, and secondary navigation

### Regression anchors
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
- `frontend/src/components/trace/run-trace-summary-view.test.tsx`
- `frontend/src/lib/__tests__/run-primary-view.test.ts`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ChatRunAnswerCard` already holds the narrative, confidence pill, inline charts, evidence disclosure, and secondary navigation in one answer shell, so Phase 21 can polish composition without reopening the data contract.
- `chat-message-list.tsx` already centers the transcript and is the right seam for width, rhythm, and answer-column tuning across viewport sizes.
- The confidence, disclosure, and chart surfaces are already componentized, which makes it possible to polish their spacing and behavior without deep refactors.

### Established Patterns
- Backend already owns answer, confidence, evidence, and chart preview semantics; Phase 21 should not push meaning back into frontend heuristics.
- The answer hierarchy is already locked and should stay intact: narrative answer first, confidence posture inline, optional charts second, supplemental evidence third, escape-hatch pills last.
- Trace is already the technical deep-dive surface in product direction; remaining ambiguity is mostly wording and navigation polish.

### Integration Points
- Responsive polish will likely touch both the transcript container and the answer subcomponents together.
- Citation/link polish should stay inside the answer renderer rather than being bolted onto trace or artifact pages.
- Final chat/trace wording alignment will likely touch answer-card navigation copy, trace-page headings, and maybe artifact/trace back-links together.

</code_context>

<deferred>
## Deferred Ideas

- New answer contract fields beyond the Phase 17 narrative preview
- New confidence semantics or explainer groupings beyond the Phase 18 contract
- New evidence-disclosure interaction models beyond the Phase 19 contract
- New chart families, controls, or exploratory chart tooling beyond the Phase 20 contract

</deferred>

---

*Phase: 21-narrative-answer-polish*
*Context gathered: 2026-04-25*
