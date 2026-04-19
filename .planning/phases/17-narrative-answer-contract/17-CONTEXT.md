# Phase 17: Narrative Answer Contract - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the short summary-card answer with a fuller narrative analyst reply that reads like the primary product output inside chat.

This phase covers the narrative answer contract itself: the structure of the answer body, where that narrative is authored, how fallback answers behave when support is limited, what voice the prose should use, and roughly how long the default answer should be.

It does not move confidence into the answer header, redesign evidence as a disclosure, or add inline charts. Those remain Phase 18, Phase 19, and Phase 20 work.

</domain>

<decisions>
## Implementation Decisions

### Narrative answer structure
- **D-01:** The default answer should start with one lead thesis sentence, then continue as 2-3 short prose sections: `What’s happening`, `Why we think that`, and `What weakens the claim`.
- **D-02:** Phase 17 should replace the current summary-card feel with a real read-through answer body rather than a headline plus stacked findings cards.

### Narrative answer source contract
- **D-03:** The backend should expose a safe narrative preview contract for chat instead of forcing the frontend to synthesize long-form prose from takeaways and caveats.
- **D-04:** The narrative answer should remain auditable and bounded by existing safe-preview patterns rather than requiring raw payload access in chat.

### Fallback answer behavior
- **D-05:** If the run cannot support a full narrative answer, the system should still return a partial-answer paragraph that says what can be stated confidently and what evidence is missing or weak.
- **D-06:** Phase 17 should avoid generic success copy, mirrored takeaway cards, or blank-looking answers as fallback behavior.

### Answer tone and voice
- **D-07:** The prose should use an analyst-memo voice: direct, cautious, concrete, and free of “assistant” framing.
- **D-08:** The answer should avoid marketing tone or generic chatbot phrasing even when the evidence is thin.

### Default answer length
- **D-09:** The default narrative answer should target roughly 120-220 words.
- **D-10:** The answer should feel substantive enough to read as the main reply, while leaving later phases room for supplemental evidence and charts below it.

### the agent's Discretion
- Exact field names and shape of the backend-safe narrative preview contract, as long as it clearly separates thesis, support, and watchouts/fallback context.
- Exact paragraph rendering pattern in chat, as long as it preserves the lead thesis plus short narrative-section structure.
- Exact heuristic for when an answer can support the full narrative contract versus when it should fall back to a partial-answer paragraph.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — v1.3 milestone framing and the product shift from summary-style answers to narrative reading
- `.planning/ROADMAP.md` — Phase 17 goal, plan breakdown, and explicit boundary against later confidence/evidence/chart phases
- `.planning/REQUIREMENTS.md` — `ANSR-01` and `ANSR-02` define the formal acceptance criteria for narrative answers and graceful fallback behavior
- `.planning/STATE.md` — current project position at the start of Phase 17

### Prior decisions that constrain this phase
- `.planning/phases/14-chat-native-result-contract/14-CONTEXT.md` — chat is already the primary answer-reading surface with one assistant slot upgraded in place
- `.planning/phases/15-evidence-navigation-in-chat/15-CONTEXT.md` — evidence is already intended to be supplemental to the answer, not a competing primary surface
- `.planning/phases/16-secondary-run-inspection/16-CONTEXT.md` — trace remains the technical deep-dive surface rather than the main reading layer

### Current answer and transparency seams
- `backend/schemas/run_transparency.py` — current safe preview contract only exposes takeaway/caveat/confidence slices, not a true narrative answer body
- `backend/api/routes/runs.py` — run detail and transparency summary assembly that will need to surface any new safe narrative fields
- `frontend/src/lib/api/types.ts` — frontend wire types for current run transparency preview data
- `frontend/src/lib/run-primary-view.ts` — current answer builder still centers `summaryLine`, takeaways, and fallback logic
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx` — current chat answer renderer that must move from summary-first to narrative-first
- `frontend/src/actions/runs.ts` — current chat action path that still falls back to summary-line style reply content
- `frontend/src/lib/chat-run-history.ts` — persisted chat-history hydration path that must stay compatible as the answer contract changes

### Regression anchors
- `tests/test_run_transparency_builders.py` — backend-safe transparency preview behavior that the new narrative contract should extend without breaking
- `tests/test_sprint3_transparency_api.py` — API-level expectations for transparency payloads
- `frontend/src/lib/__tests__/run-primary-view.test.ts` — frontend answer-view derivation tests anchored on the current summary/takeaway model
- `frontend/src/lib/chat-run-history.test.ts` — persisted chat-history reconstruction tests

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/schemas/run_transparency.py`: already defines a safe preview seam for chat-facing answer data; Phase 17 can extend this instead of inventing a separate answer API.
- `frontend/src/lib/run-primary-view.ts`: already centralizes answer derivation, fallback logic, and view-model shaping, making it the natural place to consume a new narrative contract.
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx`: already renders the centered chat answer surface, so Phase 17 can change the answer hierarchy without rebuilding the whole chat shell.
- `frontend/src/lib/chat-run-history.ts` and `frontend/src/actions/runs.ts`: already convert persisted runs and newly executed runs into chat messages, so they are the compatibility seam for rolling out the new answer contract.

### Established Patterns
- Chat is already the primary reading surface, and trace is already secondary; Phase 17 should deepen that pattern rather than reopen it.
- The current system still depends on `summaryLine`, `takeawayRows`, and caveat lists, so the narrative contract must either supersede or cleanly coexist with those fields during migration.
- Backend-safe preview data is already the trust boundary for chat, so the longer answer should be sourced from preview-safe fields rather than raw artifact parsing in the browser.

### Integration Points
- The backend narrative preview will need to connect at the transparency-summary layer and flow through existing run-detail API types.
- The frontend answer builder will need to translate the narrative preview into a new primary answer body while preserving compatibility with persisted historical runs.
- The chat answer renderer will need to promote prose as the main payload and demote summary-card patterns without yet taking on the evidence-disclosure and chart work scheduled for later phases.

</code_context>

<specifics>
## Specific Ideas

- User wants the answer to feel like “more of a chat reply + supplemental evidence” rather than “summary reply + inspect the evidence.”
- User wants the primary answer to read as a substantive analyst response, not a compressed summary card.
- User is open to other ideas, but the direction is clearly toward a longer centered reading experience in chat rather than a stack of utility cards.

</specifics>

<deferred>
## Deferred Ideas

- Inline evidence-strength badge in the answer header with a click-to-explain rating surface — Phase 18
- Supplemental evidence disclosure beneath the narrative answer, with long slim evidence cards and the five secondary pills below it — Phase 19
- Deterministic inline charts in chat using shadcn/Recharts components — Phase 20
- Further narrative-layout polish and width/spacing refinement across screen sizes — Phase 21

</deferred>

---

*Phase: 17-narrative-answer-contract*
*Context gathered: 2026-04-19*
