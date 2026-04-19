# Phase 15: Evidence Navigation in Chat - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Attach findings, confidence, caveats, and evidence navigation directly to the chat-delivered answer so the inline answer becomes a complete verification surface for normal reading and first-pass inspection.

This phase covers the answer content that still lives mostly on the standalone run page after Phase 14: top findings, confidence strip, caveats, and one compact navigation surface for report, evidence, artifacts, critic output, and trace. It also covers exact jump paths from findings or caveats into the supporting artifact or trace target when deeper validation is needed.

It does not simplify or redesign the standalone run page itself. That remains Phase 16 work.

</domain>

<decisions>
## Implementation Decisions

### Inline answer scope
- **D-01:** Phase 15 should pull top findings and structured critic/alignment cards into chat, not just add navigation links.
- **D-02:** Inline answer content should remain bounded and summary-first; Phase 15 should not dump full markdown reports or raw trace payloads into the transcript.

### Confidence and caveat placement
- **D-03:** Confidence and caveats should be visible inline within the chat answer rather than buried below the fold on the run page.
- **D-04:** Blocking caveats, weak-evidence signals, and context/budget warnings should stay compact and readable, with overflow routed into deep dive rather than turning the chat card into a wall of badges.

### Navigation surface
- **D-05:** The chat answer should expose one compact navigation area for report, evidence, artifacts, critic output, and trace instead of repeating chips under every finding.
- **D-06:** Exact evidence jumps from a finding or caveat must still exist, but they should be subordinate to the compact primary navigation area rather than the dominant reading pattern.

### Reuse and duplication boundary
- **D-07:** Phase 15 should reuse the existing structured-answer primitives and run-answer view data instead of inventing a separate chat-only evidence model.
- **D-08:** The standalone run page may continue to use the same underlying primitives for now; removing duplicated answer-reading sections is deferred to Phase 16.

### the agent's Discretion
- Exact visual hierarchy of inline findings versus caveats versus navigation as long as the answer remains compact and readable in chat
- Exact balance between always-visible evidence affordances and expandable or secondary ones
- Exact strategy for reusing existing structured-answer components in chat without importing run-page sprawl wholesale

</decisions>

<specifics>
## Specific Ideas

- Recommended direction selected autonomously:
  - show top findings and alignment cards inline in chat now
  - show confidence and caveats inline in the same chat answer
  - collapse report/evidence/artifacts/critic/trace access into one compact navigation surface
  - preserve exact evidence jumps from findings and caveats, but make them secondary to the compact nav
  - reuse existing structured-answer and `PrimaryAnswerView` primitives instead of creating a second chat-only answer model
- The current `RunPrimaryAnswer` already contains nearly all of the content Phase 15 needs; the main task is moving the right subsets into the chat answer without reproducing the page’s current fragmentation.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — v1.2 milestone framing after Phase 14
- `.planning/ROADMAP.md` — Phase 15 goal and success criteria
- `.planning/REQUIREMENTS.md` — `CHAT-02`, `NAV-01`, and `NAV-02`
- `.planning/STATE.md` — current project position after Phase 14

### Prior decisions that constrain this phase
- `.planning/phases/14-chat-native-result-contract/14-CONTEXT.md` — compact chat answer shell, one-message upgrade model, and stable run linkage already locked
- `.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md` — summary-first and bounded detail remain the preferred deep-dive pattern
- `.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md` — prompt routing and rewrite guidance are already solved and out of scope here

### Current answer and evidence surfaces
- `frontend/src/components/runs/run-primary-answer.tsx` — current home of findings, confidence, evidence, and next-step sections
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — current compact chat answer shell after Phase 14
- `frontend/src/components/chat-shell/chat-message-list.tsx` — transcript rendering path for structured answers
- `frontend/src/lib/run-primary-view.ts` — single source of derived answer/evidence data

### Reusable structured-answer primitives
- `frontend/src/components/structured-answer/top-findings-list.tsx`
- `frontend/src/components/structured-answer/finding-cards.tsx`
- `frontend/src/components/structured-answer/confidence-strip.tsx`
- `frontend/src/components/structured-answer/caveat-badge-group.tsx`
- `frontend/src/components/structured-answer/evidence-summary.tsx`
- `frontend/src/components/structured-answer/deep-dive-actions.tsx`
- `frontend/src/components/runs/verify-analysis-section.tsx`

### Secondary/deep-dive surfaces that this phase should link to, not inline entirely
- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- `frontend/src/components/transparency/report-evidence-panel.tsx`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RunPrimaryAnswer` already composes a workable section breakdown for findings, evidence, confidence, and actions, which makes Phase 15 primarily an extraction and recomposition problem.
- `PrimaryAnswerView` already carries the data Phase 15 needs: takeaway rows, alignment findings, evidence links, confidence fields, caveats, weak-evidence signals, and provenance hints.
- The new `ChatRunAnswerCard` from Phase 14 already established the answer shell and run strip, so Phase 15 can extend that shell rather than rebuild the answer from scratch.

### Established Patterns
- Chat answers are now one assistant slot per request, upgraded in place and reloadable from persisted runs.
- The run page currently mixes primary reading and verification tasks; Phase 15 should move the reading-oriented evidence sections into chat, but should not try to simplify the run page yet.
- Evidence chips already exist at finding level, but the user specifically disliked the fragmented, repetitive page structure; this phase should reduce repetition.

### Integration Points
- Phase 15 will likely expand `CompactChatAnswerView` or replace it with a richer chat answer view derived from `PrimaryAnswerView`.
- The chat answer card will need coordinated updates to layout, tests, and perhaps new helper components so it can carry findings/caveats/nav without becoming unbounded.
- The standalone run page may temporarily share more of the same primitives, but Phase 16 will decide what remains on that page afterward.

</code_context>

<deferred>
## Deferred Ideas

- Simplifying the standalone run page into a secondary inspection surface — Phase 16
- Fully persistent multi-thread chat history or cross-run comparison UX
- Raw payload or full markdown embedding directly inside the transcript

</deferred>

---

*Phase: 15-evidence-navigation-in-chat*
*Context gathered: 2026-04-19*
