# Phase 13: Analyst Prompt Routing - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-18
**Phase:** 13-Analyst Prompt Routing
**Areas discussed:** Thesis-style single-company routing, Peer/comparison language boundary, Prompt-named scope handling, Unsupported guidance contract, LLM rescue boundary

---

## Thesis-style single-company routing

| Option | Description | Selected |
|--------|-------------|----------|
| A | Route broad analyst theses to the closest deterioration/trend path when enough business cues are present | ✓ |
| B | Keep requiring explicit anomaly/deterioration keywords | |
| C | Broaden only when the prompt includes both a metric and a time horizon | |

**User's choice:** Option A.
**Notes:** User wants ordinary analyst phrasing to work without forcing users to learn the current keyword gate.

---

## Peer/comparison language boundary

| Option | Description | Selected |
|--------|-------------|----------|
| A | Accept broader relative-language cues, but do not infer peer mode from multiple tickers alone | ✓ |
| B | Treat any prompt with 2+ tickers as peer mode | |
| C | Keep the current narrow `compare`/`report` gate | |

**User's choice:** Option A.
**Notes:** User wants broader comparison language support without making every multi-ticker prompt a peer comparison.

---

## Prompt-named scope handling

| Option | Description | Selected |
|--------|-------------|----------|
| A | Narrow to the prompt-named subset when the symbols are already in the workspace; otherwise stop and guide | ✓ |
| B | Always use the full workspace scope | |
| C | Let prompt text override workspace scope and add outside symbols | |

**User's choice:** Option A.
**Notes:** User wants the system to respect named in-scope symbols while avoiding silent workspace expansion.

---

## Unsupported guidance contract

| Option | Description | Selected |
|--------|-------------|----------|
| A | Return 2-3 concrete rewrite suggestions based on the current prompt shape and workspace scope | ✓ |
| B | Show a static generic help block | |
| C | Auto-run the closest supported route even when confidence is low | |

**User's choice:** Option A.
**Notes:** User wants failure to become a useful next step rather than a dead-end planner error.

---

## LLM rescue boundary

| Option | Description | Selected |
|--------|-------------|----------|
| A | Keep deterministic-first routing, with only an explicit audited LLM rescue fallback when enabled | ✓ |
| B | Always try LLM rescue before returning unsupported | |
| C | Do not use any LLM rescue in this milestone | |

**User's choice:** Option A.
**Notes:** User wants a controlled escape hatch available later without weakening the default deterministic trust boundary.

---

## the agent's Discretion

- Exact deterministic cue expansion for thesis-style and peer-relative routing
- Exact prompt-to-workspace ticker narrowing mechanics
- Exact unsupported rewrite-guidance payload and UI surface
- Exact config and audit behavior for any optional LLM rescue path

## Deferred Ideas

- Chat-native answer rendering — Phase 14
- Evidence navigation in chat — Phase 15
- Secondary run inspection redesign — Phase 16
- New analytical modes beyond the current supported workflows
