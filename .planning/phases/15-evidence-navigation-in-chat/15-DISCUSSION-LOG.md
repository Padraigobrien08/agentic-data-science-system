# Phase 15: Evidence Navigation in Chat - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 15-Evidence Navigation in Chat
**Areas discussed:** Inline findings scope, confidence and caveat placement, navigation surface, reuse boundary

---

## Inline findings scope

| Option | Description | Selected |
|--------|-------------|----------|
| A | Pull top findings and alignment cards into chat now, but keep the answer bounded and summary-first | ✓ |
| B | Keep findings on the run page and only add navigation links in chat | |
| C | Move the full run-page content into the chat answer | |

**Chosen autonomously:** Option A.
**Notes:** The user wants the answer to live in chat, not another link farm or a copy of the full run page.

---

## Confidence and caveat placement

| Option | Description | Selected |
|--------|-------------|----------|
| A | Show confidence and caveats inline in the chat answer with bounded overflow to deep dive | ✓ |
| B | Keep confidence and caveats primarily on the run page | |
| C | Show every caveat badge and weak-evidence detail inline without bounds | |

**Chosen autonomously:** Option A.
**Notes:** Confidence and caveats are part of reading the answer, so they should move with it, but the chat card still needs density control.

---

## Navigation surface

| Option | Description | Selected |
|--------|-------------|----------|
| A | One compact navigation area for report, evidence, artifacts, critic output, and trace, with exact jumps still available secondarily | ✓ |
| B | Keep per-finding chips as the dominant navigation pattern | |
| C | Hide most navigation and force users onto the run page for evidence inspection | |

**Chosen autonomously:** Option A.
**Notes:** This directly matches the user’s complaint about repeated chips and fragmented navigation.

---

## Reuse boundary

| Option | Description | Selected |
|--------|-------------|----------|
| A | Reuse the existing structured-answer primitives and answer view data in chat | ✓ |
| B | Create a separate chat-only answer/evidence model | |
| C | Move all logic into the chat component first, then clean it up later | |

**Chosen autonomously:** Option A.
**Notes:** Brownfield safety and milestone speed both favor reuse; the run page cleanup comes next in Phase 16.

---

## Deferred Ideas

- Standalone run page simplification — Phase 16
- Fully persisted multi-conversation chat threads
- Full markdown/raw payload embedding in chat
