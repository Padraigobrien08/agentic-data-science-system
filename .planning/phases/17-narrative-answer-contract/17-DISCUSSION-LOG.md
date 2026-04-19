# Phase 17: Narrative Answer Contract - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-19
**Phase:** 17-Narrative Answer Contract
**Areas discussed:** Narrative answer structure, Narrative answer source contract, Fallback answer behavior, Answer tone and voice, Default answer length

---

## Narrative answer structure

| Option | Description | Selected |
|--------|-------------|----------|
| A | Lead thesis sentence, then 3 short prose sections: `What’s happening`, `Why we think that`, `What weakens the claim` | ✓ |
| B | One longer uninterrupted essay-style answer | |
| C | Thesis plus bullet-heavy body | |

**User's choice:** Option A.
**Notes:** User wants the answer to feel like a real chat reply rather than another summary-card layout.

---

## Narrative answer source contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Backend exposes a safe narrative preview contract, and frontend renders it | ✓ |
| B | Frontend assembles the narrative from existing takeaways/caveats | |
| C | Hybrid: backend provides a lead answer only, frontend expands the rest | |

**User's choice:** Option A.
**Notes:** User wants a deliberate narrative answer contract rather than longer prose stitched together from current fragments.

---

## Fallback answer behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A | If support is limited, return a partial answer paragraph that says what can be said confidently and what is missing | ✓ |
| B | If support is limited, show no answer body and only a limitation notice | |
| C | If support is limited, reuse the strongest takeaway card as the whole answer | |

**User's choice:** Option A.
**Notes:** User does not want blank or vague “successful but empty” answers; fallback should still read like a useful reply.

---

## Answer tone and voice

| Option | Description | Selected |
|--------|-------------|----------|
| A | Analyst memo voice: direct, cautious, concrete, no assistant framing | ✓ |
| B | Conversational assistant voice | |
| C | Highly formal research-note voice | |

**User's choice:** Option A.
**Notes:** The target is trustworthy analyst prose, not chatbot tone and not overly academic writing.

---

## Default answer length

| Option | Description | Selected |
|--------|-------------|----------|
| A | Roughly `120-220` words by default | ✓ |
| B | Roughly `220-400` words by default | |
| C | Dynamic length with no target | |

**User's choice:** Option A.
**Notes:** User wants a longer answer than today, but still short enough that later evidence and chart layers remain supplemental.

---

## the agent's Discretion

- Exact backend-safe field shape for the new narrative answer preview
- Exact frontend rendering details for the prose sections
- Exact fallback threshold for full-answer versus partial-answer mode

## Deferred Ideas

- Evidence-strength badge and explainer — Phase 18
- Supplemental evidence disclosure layout — Phase 19
- Inline charts in chat with shadcn/Recharts — Phase 20
- Final narrative-layout polish across screen sizes — Phase 21
