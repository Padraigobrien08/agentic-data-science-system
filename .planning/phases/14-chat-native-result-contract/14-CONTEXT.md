# Phase 14: Chat-Native Result Contract - Context

**Gathered:** 2026-04-19
**Status:** Ready for planning

<domain>
## Phase Boundary

Make completed run results first-class chat answers with stable run linkage so the workspace conversation becomes the primary place users read the result.

This phase covers the chat answer contract itself: what answer content moves inline, how a pending assistant message becomes the final answer, how chat reloads that result from persisted run state, and how the message visibly links back to the underlying run.

It does not add inline findings/caveats/evidence navigation beyond the compact primary answer block, and it does not redesign the standalone run page. Those remain Phase 15 and Phase 16 work.

</domain>

<decisions>
## Implementation Decisions

### Inline answer scope
- **D-01:** Phase 14 should move a compact primary answer block into chat, not the full current run-answer experience.
- **D-02:** Top findings, caveats, confidence strips, and compact evidence navigation remain later-scope work for Phase 15.

### Pending-to-final update model
- **D-03:** Each user prompt should own one assistant message slot that upgrades in place from pending state to the final structured answer.
- **D-04:** Phase 14 should avoid duplicate “run started / run finished / final answer” assistant chatter for the same request.

### History and reload model
- **D-05:** Chat should hydrate reload-safe history from persisted project runs instead of relying only on the current local-only in-memory session stubs.
- **D-06:** Phase 14 should not introduce fully persisted multi-conversation chat threads yet; reuse the existing project-run history as the stable backbone.

### Run linkage visibility
- **D-07:** Each completed chat answer should show a compact run identity strip with status, timestamp, and one primary open-run action.
- **D-08:** Richer navigation and multi-link evidence surfaces should wait for later phases instead of recreating the current run-page link sprawl inside chat.

### Follow-up semantics
- **D-09:** Follow-up prompts should remain new analyses in the same visible thread rather than trying to mutate or replace the prior run.
- **D-10:** Phase 14 should not yet auto-inject prior run context into the next request; continuity should stay visible and user-driven rather than implicit.

### the agent's Discretion
- Exact structure of the compact primary answer block as long as it reuses the existing run-answer semantics rather than inventing a second answer language
- Exact strategy for hydrating chat from persisted runs while the app still lacks real persisted conversation threads
- Exact visual design of the compact run identity strip and the single primary run action
- Exact pending-state presentation while the assistant message upgrades in place

</decisions>

<specifics>
## Specific Ideas

- User chose the recommended direction on all Phase 14 gray areas:
  - move a compact primary answer block into chat now, while deferring findings/caveats/navigation depth to later phases
  - keep one assistant message per request and upgrade it in place from pending to final
  - hydrate reload-safe history from persisted project runs, but do not add full persisted chat-thread infrastructure yet
  - show a compact run identity strip with one primary open-run action
  - keep follow-up prompts as new analyses in the same visible thread, without implicit prior-run context injection
- The user wants the primary reading experience to move into chat, but not by cloning the full standalone run page inside the transcript.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — v1.2 milestone framing and the remaining product gap after Phase 13
- `.planning/ROADMAP.md` — Phase 14 goal and success criteria
- `.planning/REQUIREMENTS.md` — `CHAT-01` and `CHAT-03` define the formal acceptance criteria
- `.planning/STATE.md` — current project position after Phase 13 completion

### Prior decisions that constrain this phase
- `.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md` — chat remains sync-first for now and background posture must stay truthful
- `.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md` — prompt routing and unsupported rewrite guidance are already solved, so Phase 14 should build on that rather than reopen it
- `.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md` — summary-first, bounded detail is already the preferred pattern for deep-dive surfaces

### Current chat and run-answer seams
- `frontend/src/app/projects/[projectId]/chat/page.tsx` — current chat page framing still points users toward run answer and deep dive links
- `frontend/src/components/chat-shell/chat-shell.tsx` — current local-only session state, pending assistant message flow, and assistant reply hydration
- `frontend/src/components/chat-shell/chat-message-list.tsx` — current transcript rendering, including unsupported guidance and run/deep-dive links
- `frontend/src/components/chat-shell/types.ts` — current assistant message contract
- `frontend/src/actions/runs.ts` — current preview/create/execute chat action that still returns plain assistant text plus links
- `frontend/src/components/chat-shell/assistant-structured-frame.tsx` — existing placeholder for structured assistant blocks

### Existing structured answer assets
- `frontend/src/lib/run-primary-view.ts` — current builder for structured run-answer view data
- `frontend/src/components/runs/run-primary-answer.tsx` — current primary answer surface on the standalone run page
- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx` — current run-detail composition and link treatment
- `frontend/src/lib/run-status-copy.ts` — existing user-facing status and in-flight/error copy patterns

### Current API and persistence surfaces
- `frontend/src/lib/api/runs.ts` and `frontend/src/lib/api/types.ts` — current run fetch, run detail, and trace-summary contracts
- `backend/api/routes/runs.py` — current run detail and execute surfaces that chat can reuse
- `backend/models/analysis_run.py` and related run-step/artifact models — persisted run state that can back reload-safe chat history

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `run-primary-view.ts` already derives a compact structured answer model from persisted run payloads without adding a new backend API.
- `run-primary-answer.tsx` already splits the run answer into separable sections, which means Phase 14 can likely extract or reuse only the top summary layer instead of duplicating the whole run page.
- `assistant-structured-frame.tsx` already exists as a placeholder for structured assistant output, so the chat surface has an intended insertion point for non-prose answer content.
- `createAnalysisRunFromChat` in `frontend/src/actions/runs.ts` already owns the full chat request lifecycle, making it the natural place to return a richer answer contract tied to the created run.

### Established Patterns
- Chat is still local-only UI state: session stubs and messages live in client memory and do not survive reload.
- The current assistant reply is still a plain text status line plus run links, even though the product already has a richer structured run-answer surface elsewhere.
- The run answer already treats summary-first reading as distinct from deep dive, which aligns with the milestone goal of moving the primary reading layer into chat while keeping inspection routes secondary.
- Unsupported routing already returns inline rewrite guidance in the transcript, so Phase 14 should preserve that conversation pattern rather than regress to redirects or dead-end pages.

### Integration Points
- Phase 14 likely needs coordinated changes across `runs.ts`, chat message types, chat rendering, and the existing run-answer view builders so the chat answer stays consistent with the standalone run answer.
- Reload-safe history will likely need a project-scoped mapping from persisted `AnalysisRun` records into chat transcript rows without introducing a full chat-thread persistence model yet.
- The compact run identity strip should integrate with existing run status, timestamps, and navigation patterns rather than inventing a second run metadata language.

</code_context>

<deferred>
## Deferred Ideas

- Inline findings, confidence, caveats, and compact evidence navigation — Phase 15
- Simplified standalone run page as a secondary inspection surface — Phase 16
- Fully persisted multi-conversation chat threads
- Implicit prior-run conversational memory or automatic context carry-forward between chat prompts

</deferred>

---

*Phase: 14-chat-native-result-contract*
*Context gathered: 2026-04-19*
