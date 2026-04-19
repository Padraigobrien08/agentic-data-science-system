# Phase 14: Chat-Native Result Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 14-Chat-Native Result Contract
**Areas discussed:** Inline answer scope, Pending-to-final update model, History and reload model, Run linkage visibility, Follow-up semantics

---

## Inline answer scope

| Option | Description | Selected |
|--------|-------------|----------|
| A | Move a compact primary answer block into chat now, while leaving findings/caveats/navigation depth for later phases | ✓ |
| B | Recreate the full standalone run answer inside chat immediately | |
| C | Keep chat as status text only until all later answer-navigation phases are done | |

**User's choice:** Option A.
**Notes:** User wants chat to become the main reading surface, but not by dumping the full current run page into the transcript.

---

## Pending-to-final update model

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep one assistant message per request and upgrade it in place from pending to final | ✓ |
| B | Post a second assistant message when the final answer is ready | |
| C | Replace the whole thread view with the latest run answer | |

**User's choice:** Option A.
**Notes:** User wants continuity in the conversation rather than duplicate completion chatter.

---

## History and reload model

| Option | Description | Selected |
|--------|-------------|----------|
| A | Hydrate chat from persisted project runs, but do not add full persisted chat-thread infrastructure yet | ✓ |
| B | Keep chat local-only for now | |
| C | Add full persisted multi-conversation chat threads in this phase | |

**User's choice:** Option A.
**Notes:** User wants reload-safe history, but Phase 14 should stay focused on result delivery rather than expanding into a full chat persistence product.

---

## Run linkage visibility

| Option | Description | Selected |
|--------|-------------|----------|
| A | Show a compact run identity strip with status, timestamp, and one primary open-run action | ✓ |
| B | Keep the current multiple text links in chat | |
| C | Hide run linkage entirely once the answer is in chat | |

**User's choice:** Option A.
**Notes:** User wants explicit linkage back to the underlying run without recreating the current link clutter.

---

## Follow-up semantics

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep follow-up prompts as new analyses in the same visible thread, without auto-injecting prior run context | ✓ |
| B | Auto-carry previous run context into every follow-up prompt | |
| C | Split every prompt into a separate isolated conversation | |

**User's choice:** Option A.
**Notes:** User wants visible continuity, but not implicit conversational memory or hidden carry-forward semantics yet.

---

## the agent's Discretion

- Exact structure of the compact answer block inside chat
- Exact reload-safe mapping from persisted runs into the visible transcript
- Exact visual treatment of the compact run identity strip
- Exact pending-state UI while an assistant message upgrades in place

## Deferred Ideas

- Inline findings, caveats, confidence, and evidence navigation in chat — Phase 15
- Standalone run page simplification — Phase 16
- Fully persisted multi-conversation chat threads
- Automatic prior-run context carry-forward between prompts
