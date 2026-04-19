# Phase 14: Chat-Native Result Contract - Research

**Researched:** 2026-04-19
**Domain:** Move the primary run answer into workspace chat with stable run linkage, reload-safe history, and in-place message updates
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Phase 14 should move a compact primary answer block into chat, not the full current run-answer experience.
- **D-02:** Top findings, caveats, confidence strips, and compact evidence navigation remain later-scope work for Phase 15.
- **D-03:** Each user prompt should own one assistant message slot that upgrades in place from pending state to the final structured answer.
- **D-04:** Phase 14 should avoid duplicate “run started / run finished / final answer” assistant chatter for the same request.
- **D-05:** Chat should hydrate reload-safe history from persisted project runs instead of relying only on the current local-only in-memory session stubs.
- **D-06:** Phase 14 should not introduce fully persisted multi-conversation chat threads yet; reuse the existing project-run history as the stable backbone.
- **D-07:** Each completed chat answer should show a compact run identity strip with status, timestamp, and one primary open-run action.
- **D-08:** Richer navigation and multi-link evidence surfaces should wait for later phases instead of recreating the current run-page link sprawl inside chat.
- **D-09:** Follow-up prompts should remain new analyses in the same visible thread rather than trying to mutate or replace the prior run.
- **D-10:** Phase 14 should not yet auto-inject prior run context into the next request; continuity should stay visible and user-driven rather than implicit.

### the agent's Discretion
- Exact structure of the compact primary answer block as long as it reuses the existing run-answer semantics rather than inventing a second answer language
- Exact strategy for hydrating chat from persisted runs while the app still lacks real persisted conversation threads
- Exact visual design of the compact run identity strip and the single primary run action
- Exact pending-state presentation while the assistant message upgrades in place

### Deferred Ideas (OUT OF SCOPE)
- Inline findings, confidence, caveats, and compact evidence navigation in chat
- Simplified standalone run page as a secondary inspection surface
- Fully persisted multi-conversation chat threads
- Implicit prior-run conversational memory or automatic context carry-forward between chat prompts
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHAT-01 | User can receive the completed analysis answer as a workspace chat message instead of using the standalone run page as the primary place to read the result | Reuse the existing run-answer derivation path and render a compact answer card in the assistant message instead of plain status text plus links. |
| CHAT-03 | User can continue the workspace conversation after a completed run while retaining visible linkage to the run that produced the answer | Keep one assistant message per request, persist linkage through reload-safe run-backed history, and show a compact run identity strip for each completed answer. |
</phase_requirements>

## Summary

Phase 14 is mostly a reuse-and-reframe problem, not a brand-new answer system. The repo already has a structured primary answer model in `frontend/src/lib/run-primary-view.ts` and a rich standalone render surface in `frontend/src/components/runs/run-primary-answer.tsx`. The current chat path simply stops too early: `frontend/src/actions/runs.ts` creates and executes a run, then returns plain assistant text plus `runHref` and `deepDiveHref`. That means the product already has the answer content, but it is only readable on the standalone run page.

The safest brownfield move is to split “answer derivation” from “run page composition” and reuse the existing derivation logic inside chat. `buildPrimaryAnswerView(...)` already turns persisted `AnalysisRun` payloads and artifacts into a typed summary model. Phase 14 should reuse that builder, but render only a compact subset in chat: summary line, goal text, orchestration or run status cues, conclusion rider when present, and a compact run identity strip. It should not mount the full `RunPrimaryAnswer` tree in chat, because that would pull Phase 15 and Phase 16 scope forward immediately.

The biggest architectural seam is history persistence. `ChatShell` is still local-only state with fake `local-1` sessions and a “New conversation” sidebar that does not survive reload. The user explicitly rejected building a full persisted conversation system in this phase, so the recommended bridge is to treat persisted project runs as the durable chat history source. The page can server-render a bounded transcript from recent project runs, then let the client continue appending new prompts and upgrading the current pending assistant slot in place. That satisfies reload-safe continuity without inventing a new tables-and-thread model.

Because the current chat action already owns the request lifecycle, the pending-to-final upgrade can stay simple. `createAnalysisRunFromChat(...)` should keep returning a single reply object for the matching assistant slot, but instead of only `content` plus links, it should return a typed compact answer payload once execution completes. The client already knows how to replace the pending assistant message in place by `requestId`, so the phase can preserve conversation continuity without adding streaming or duplicate final messages.

A compact run identity strip is the right explicit linkage mechanism for this phase. The current chat reply exposes three links (`Run answer`, `Deep dive`, `All runs`), while the user asked for one primary action and Phase 15 will handle richer navigation later. The answer card should therefore carry a small status/timestamp/run-id or run-label strip with one primary open-run action. That keeps the run legible as a durable artifact without recreating the current run-page link clutter inside the transcript.

One important product consequence: the current sidebar’s multiple local “conversations” become misleading once persisted run history backs the visible transcript. Phase 14 does not need to solve full conversation threading, but it should stop pretending that client-only tabs are durable. The lowest-risk recommendation is to pivot the chat surface toward one workspace-level conversation history for now, or at least make any additional local sessions clearly ephemeral until a later milestone adds real persistence.

**Primary recommendation:** plan Phase 14 as **3 sequential plans**. First, carve out a compact chat-answer contract from the existing run-answer derivation path and message types. Second, hydrate the chat transcript from persisted project runs and use that same contract to render reload-safe history plus in-place pending-to-final updates. Third, add the compact run identity strip, reduce the old multi-link behavior, and harden the chat tests and build gate. That shape satisfies `CHAT-01` and `CHAT-03` without pulling Phase 15 evidence navigation or Phase 16 run-page simplification forward.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or project-root `.agents/skills/` directory exists under `/Users/padraigobrien/agentic_data_science_system`.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Existing Next.js App Router server-rendered page flow | Next.js 15 / React 19 | Server-render initial chat transcript from persisted runs and pass typed data into client chat shell | The repo already prefers server-side data access in `frontend/src/app/**` plus server-only API wrappers. |
| `frontend/src/lib/run-primary-view.ts` | in-repo seam | Derive compact answer view data from persisted run payloads | This already encodes the product’s answer semantics and avoids inventing a second answer language. |
| `frontend/src/actions/runs.ts` | in-repo seam | Upgrade the pending assistant message into a structured final answer after synchronous execution | The current chat action already owns preview, create, and execute for chat submissions. |
| `frontend/src/components/chat-shell/*` | in-repo seam | Host transcript rendering, pending-state replacement, and compact run linkage | Chat already has the message lifecycle seam; it just needs a richer assistant contract. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `frontend/src/components/runs/run-primary-answer.tsx` and `structured-answer/*` | in-repo seam | Reuse or extract only the top summary strata that belong in chat | Use to avoid duplicating summary semantics, but do not mount the full standalone run page inside the transcript. |
| `frontend/src/lib/api/runs.ts` + `frontend/src/lib/api/types.ts` | in-repo seam | Fetch bounded recent runs and their detail payloads for transcript hydration | Use when mapping persisted project runs into chat history without new chat persistence APIs. |
| `frontend/src/lib/run-status-copy.ts` | in-repo seam | Keep error, partial, no-data, and in-flight copy consistent between run page and chat answer states | Use for status parity once compact answer cards can represent non-success outcomes. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Reusing `buildPrimaryAnswerView(...)` and rendering a compact subset in chat | Build a separate chat-specific answer parser from raw payload JSON | Faster to prototype, but it duplicates product semantics and risks drift from the standalone run answer. |
| Hydrating chat history from persisted project runs | Keep chat local-only until full thread persistence exists | Simpler short-term, but it fails the reload-safe linkage requirement and keeps chat secondary. |
| One assistant slot that upgrades in place | Post a second “final answer” assistant message after execution | Easier to implement, but it creates duplicate transcript chatter and weakens the one-request-one-answer model. |
| A compact run identity strip with one primary action | Keep the current three text links in chat | Lowest change, but it recreates the exact fragmentation the milestone is trying to remove. |
| One workspace-level persisted history seam for now | Add full persisted multi-conversation chat threads in Phase 14 | More ambitious, but it broadens scope beyond the current milestone requirement and adds new persistence/product complexity. |

## Recommended Patterns

### Pattern 1: Reuse the Existing Answer Builder, Not the Whole Run Page

**What:** Keep `buildPrimaryAnswerView(...)` as the source of truth for answer semantics, then render a compact chat-specific answer card from that view.

**When to use:** Final assistant replies for completed runs and reload-safe hydrated history rows.

**Why:** The run answer already contains the product’s answer logic. Chat should reuse that logic but render a reduced subset appropriate to Phase 14.

**Recommended compact answer content:**
- goal or prompt display
- one summary line or conclusion block
- orchestration or run status label
- conclusion rider when present
- compact run identity strip

**Do not include yet:**
- top findings list
- evidence summary
- confidence or caveat strip
- next-step action rail beyond the single primary run action

### Pattern 2: Persisted Runs Are the Durable Chat Backbone

**What:** Build the initial chat transcript from a bounded set of persisted project runs instead of only local client state.

**When to use:** Initial load or refresh of `/projects/[projectId]/chat`.

**Why:** The user wants reload-safe continuity but explicitly does not want full chat-thread persistence in this phase.

**Recommended behavior:**
- fetch a bounded recent run list for the project
- fetch enough per-run detail to derive compact answer cards for those runs
- map each run to a user prompt row plus one assistant answer row in the visible transcript
- preserve one canonical workspace-level visible conversation for now rather than pretending local tabs are durable

### Pattern 3: Pending Assistant Messages Should Upgrade In Place

**What:** The pending assistant placeholder created on submit should become the final structured answer for that same request once execution returns.

**When to use:** Every new chat-triggered run in Phase 14.

**Why:** This preserves a stable one-request-one-answer shape in the conversation and avoids duplicate run-complete chatter.

**Recommended contract:**
- key the pending assistant message by `requestId`
- return a typed answer payload from the action once the run completes
- replace the pending slot with the final compact answer payload plus run identity strip
- preserve unsupported rewrite-guidance messages as the non-run branch

### Pattern 4: Use a Compact Run Identity Strip, Not Link Sprawl

**What:** Replace the current multi-link footer in successful chat replies with a small identity strip plus one primary open-run action.

**When to use:** Every completed structured answer in chat.

**Why:** The user wants explicit run linkage without recreating the fragmented run/deep-dive link surface inside the transcript.

**Recommended strip fields:**
- run status
- completed or updated timestamp
- optional short run id or stable label
- one primary action such as `Open run`

### Pattern 5: Keep Follow-Ups Visible, Not Implicit

**What:** Keep follow-up prompts as new analyses in the same visible thread, but do not silently feed prior run context into subsequent requests.

**When to use:** Every prompt after the first completed answer.

**Why:** The user wants continuity in one thread, but not hidden conversational memory semantics yet.

**Recommended behavior:**
- each follow-up creates a new run
- prior answer cards remain visible in the same transcript
- new prompts still use the current workspace scope and explicit prompt text only
- if future work needs carry-forward semantics, that should be introduced explicitly in a later phase

## Implementation Slices

### Slice A: Compact Chat Answer Contract

Focus files:
- `frontend/src/lib/run-primary-view.ts`
- `frontend/src/components/runs/run-primary-answer.tsx`
- `frontend/src/components/chat-shell/types.ts`
- `frontend/src/components/chat-shell/assistant-structured-frame.tsx`
- `frontend/src/actions/runs.ts`

Deliver:
- a typed compact chat-answer payload derived from persisted run data
- a reduced answer component or extracted summary component for chat use
- action return shape that can upgrade a pending assistant message into the final compact answer

### Slice B: Reload-Safe Transcript Hydration

Focus files:
- `frontend/src/app/projects/[projectId]/chat/page.tsx`
- `frontend/src/components/chat-shell/chat-shell.tsx`
- `frontend/src/components/chat-shell/chat-sidebar.tsx`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/lib/api/types.ts`

Deliver:
- server-rendered initial transcript from persisted project runs
- bounded history loading that survives reload
- a clearer workspace-history model that does not imply fully persisted multi-thread chat

### Slice C: Compact Linkage and Regression Hardening

Focus files:
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
- `frontend/src/actions/runs.test.ts`
- `frontend/src/app/projects/[projectId]/chat/page.tsx`

Deliver:
- compact run identity strip with one primary run action
- in-place pending-to-final update behavior
- regression coverage for hydrated history, structured answer rendering, and preserved unsupported-guidance behavior

## Validation Architecture

Phase 14 is primarily a frontend contract and server-action phase. The existing backend run APIs already provide most of the needed data, so the main validation burden is on typed view derivation, transcript hydration, and chat rendering behavior.

**Recommended quick command:**
```bash
cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx
```

**Recommended full command:**
```bash
cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build
```

**Required new or expanded tests:**
- `frontend/src/actions/runs.test.ts`
  - supported synchronous runs return a typed compact answer payload rather than plain text plus link-only replies
  - pending request ids still map to one final answer slot
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
  - completed structured answers render a compact answer block and compact run strip
  - unsupported rewrite-guidance messages still render without run links
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
  - initial hydrated history appears on load
  - pending assistant rows upgrade in place rather than duplicating
- new or expanded test around the compact answer derivation seam
  - either a dedicated `run-primary-view` test or a component-level test proving the compact chat answer stays aligned with the existing answer builder

## Pitfalls and Boundaries

- Do not duplicate answer parsing logic separately for chat and run page.
- Do not mount the full `RunPrimaryAnswer` surface inside chat; that pulls Phase 15 and 16 scope forward.
- Do not keep the current local-only fake session model as the only source of truth if reload-safe history is required.
- Do not introduce a full chat-thread persistence model in this phase.
- Do not regress unsupported routing guidance back into failed runs or redirects.
- Do not silently inject prior run context into follow-up prompts.

## Recommended Plan Shape

Phase 14 should be planned as **3 sequential plans**:

1. **Compact answer contract** — extract or build a compact chat answer surface from the existing run-answer derivation path
2. **Persisted-run transcript hydration** — render reload-safe chat history from project runs and upgrade pending answers in place
3. **Run linkage and hardening** — replace link sprawl with a compact run strip and lock the behavior with focused frontend regressions

This sequence keeps the answer contract first, the reload-safe history model second, and the visible chat polish and regression hardening last.

## Sources

### Primary
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/14-chat-native-result-contract/14-CONTEXT.md`
- `.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md`
- `.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md`
- `frontend/src/app/projects/[projectId]/chat/page.tsx`
- `frontend/src/components/chat-shell/chat-shell.tsx`
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- `frontend/src/components/chat-shell/chat-sidebar.tsx`
- `frontend/src/components/chat-shell/types.ts`
- `frontend/src/components/chat-shell/assistant-structured-frame.tsx`
- `frontend/src/actions/runs.ts`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/run-primary-view.ts`
- `frontend/src/components/runs/run-primary-answer.tsx`
- `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`
- `frontend/src/lib/run-status-copy.ts`

### Tests and regression anchors
- `frontend/src/actions/runs.test.ts`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
