# Phase 19: Supplemental Evidence Disclosure - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-24
**Phase:** 19-Supplemental Evidence Disclosure
**Areas discussed:** Disclosure default state, Evidence card shape, Disclosure contents, Pill placement, Thin/missing evidence behavior

---

## Disclosure default state

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep supplemental evidence collapsed by default, with one clear disclosure | ✓ |
| B | Auto-open when evidence is strong | |
| C | Remember open/closed state per workspace | |

**User's choice:** Option A.  
**Notes:** The answer should remain the default reading path; evidence becomes an intentional reveal.

---

## Evidence card shape

| Option | Description | Selected |
|--------|-------------|----------|
| A | Long, slim rows with a short title, one “why it matters” sentence, and one exact jump link | ✓ |
| B | Keep current card shapes and only restyle them | |
| C | Use an accordion list instead of cards | |

**User's choice:** Option A.  
**Notes:** The current stacked support cards underuse chat width and still feel too utility-heavy.

---

## Disclosure contents

| Option | Description | Selected |
|--------|-------------|----------|
| A | Merge takeaways and alignment/finding cards into one unified supplemental evidence list | ✓ |
| B | Keep them as separate subsections inside the disclosure | |
| C | Show only takeaways and defer alignment findings to trace | |

**User's choice:** Option A.  
**Notes:** One proof layer is cleaner than preserving multiple support sections inside the answer.

---

## Pill placement

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep `Report / Evidence / Artifacts / Critic / Trace` below the disclosure, always visible but secondary | ✓ |
| B | Move the pills inside the disclosure footer | |
| C | Move the pills into the answer header | |

**User's choice:** Option A.  
**Notes:** The pills remain useful escape hatches, but they should not compete with the answer or the supporting evidence rows.

---

## Thin or missing evidence behavior

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep the disclosure present and show a compact limited-evidence/empty-evidence state when opened | ✓ |
| B | Hide the disclosure entirely when evidence is missing | |
| C | Replace the disclosure with a one-line warning only | |

**User's choice:** Option A.  
**Notes:** The product should communicate that evidence was checked and found thin, not leave users guessing whether it failed to load.

---

## the agent's Discretion

- Exact disclosure label copy and motion/chevron treatment
- Exact merged supplemental evidence row layout
- Exact limited-evidence empty-state copy and styling

## Deferred Ideas

- Per-user remembered disclosure state
- Inline charts in the answer body — Phase 20
- Final narrative/evidence responsive polish — Phase 21
