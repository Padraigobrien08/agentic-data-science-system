---
phase: 17
slug: narrative-answer-contract
status: complete
created: 2026-04-19
---

# Phase 17: Narrative Answer Contract - Research

**Researched:** 2026-04-19
**Domain:** Replace the short summary-first chat answer with a backend-authored narrative analyst reply that still fails gracefully when support is limited
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** The default answer should start with one lead thesis sentence, then continue as 2-3 short prose sections: `What’s happening`, `Why we think that`, and `What weakens the claim`.
- **D-02:** Phase 17 should replace the current summary-card feel with a real read-through answer body rather than a headline plus stacked findings cards.
- **D-03:** The backend should expose a safe narrative preview contract for chat instead of forcing the frontend to synthesize long-form prose from takeaways and caveats.
- **D-04:** The narrative answer should remain auditable and bounded by existing safe-preview patterns rather than requiring raw payload access in chat.
- **D-05:** If the run cannot support a full narrative answer, the system should still return a partial-answer paragraph that says what can be stated confidently and what evidence is missing or weak.
- **D-06:** Phase 17 should avoid generic success copy, mirrored takeaway cards, or blank-looking answers as fallback behavior.
- **D-07:** The prose should use an analyst-memo voice: direct, cautious, concrete, and free of “assistant” framing.
- **D-08:** The answer should avoid marketing tone or generic chatbot phrasing even when the evidence is thin.
- **D-09:** The default narrative answer should target roughly 120-220 words.
- **D-10:** The answer should feel substantive enough to read as the main reply, while leaving later phases room for supplemental evidence and charts below it.

### the agent's Discretion
- Exact field names and shape of the backend-safe narrative preview contract, as long as it clearly separates thesis, support, and watchouts or fallback context
- Exact paragraph rendering pattern in chat, as long as it preserves the lead thesis plus short narrative-section structure
- Exact heuristic for when an answer can support the full narrative contract versus when it should fall back to a partial-answer paragraph

### Deferred Ideas (OUT OF SCOPE)
- Inline evidence-strength badge and explainer in the answer header
- Supplemental evidence disclosure beneath the answer
- Inline deterministic charts in chat
- Final narrative-layout polish and responsiveness tuning
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANSR-01 | User can read a multi-paragraph analyst answer in chat that explains the thesis, supporting evidence, and watchouts instead of a one-line summary card | Add a backend-safe narrative preview contract and render it as the primary chat payload instead of treating `summaryLine` as the main answer. |
| ANSR-02 | User can receive a stable non-boilerplate fallback answer when evidence is limited, so successful runs never collapse into vague placeholder text | Define explicit fallback narrative fields and preserve them through both live chat replies and persisted history hydration. |
</phase_requirements>

## Summary

Phase 17 is primarily a contract migration, not a net-new UI system. The current product already has a centered chat answer surface, but the data model underneath it is still summary-first. `frontend/src/lib/run-primary-view.ts` centers `summaryLine`, `takeawayRows`, `blockingCaveats`, and derived navigation. `frontend/src/components/chat-shell/chat-run-answer-card.tsx` then renders those findings as the main reading surface. That is why the answer still reads like a compact result card rather than a substantive analyst reply.

The safest brownfield move is to extend the existing safe preview seam on the backend rather than synthesizing narrative prose on the frontend. `backend/schemas/run_transparency.py` already exposes safe report and critic slices such as `report_key_takeaways_preview`, `critic_blocking_caveats`, and confidence/status fields. The frontend recently started relying on those preview fields specifically to avoid empty chat answers when raw payloads are not present. Phase 17 should continue in that direction by promoting a narrative answer preview into the same transparency layer and flowing it through the existing run detail contract. That preserves the trust boundary: chat still renders backend-safe answer fields rather than reconstructing analysis prose from artifacts in the browser.

The current frontend answer builder is still the migration seam. `buildPrimaryAnswerView(...)` in `frontend/src/lib/run-primary-view.ts` already normalizes raw run state, detects generic success summaries, and falls back to takeaway-derived content when necessary. It also exports `buildCompactChatAnswerView(...)` and `buildChatAnswerCardView(...)`, which means the system already has one place where answer semantics are converted into chat-facing structures. Phase 17 should preserve that architecture but swap the primary payload from `summaryLine` plus lists into a new narrative body shape. The migration should be additive first: introduce narrative fields, derive them preferentially, keep summary-era fields long enough to preserve history compatibility, then gradually demote the old fields from being the main reading surface.

The major product requirement is graceful degradation. The user explicitly does not want blank answers or vague success placeholders, but also does not want unsupported certainty. The best pattern is not “hide the answer” and not “reuse the first finding as prose.” Instead, the backend should emit a partial-answer narrative when the evidence does not support the full contract. That partial answer can still use the same prose structure, but the `What weakens the claim` section becomes the center of gravity: it should explicitly say what is missing, thin, or insufficient. This keeps chat readable while remaining honest.

The recommended architecture is therefore: backend-safe narrative preview fields in transparency, frontend answer-builder preference ordering that uses narrative fields first and summary-era fields only as compatibility fallback, and a chat renderer that treats narrative prose as the primary payload while leaving evidence-heavy restructuring to later phases. That directly satisfies `ANSR-01` and `ANSR-02` without pulling Phase 18-20 work forward.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or project-root `.agents/skills/` directory exists under `/Users/padraigobrien/agentic_data_science_system`.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `backend/schemas/run_transparency.py` | in-repo seam | Safe preview contract for chat-facing answer data | Already the trusted backend boundary for report/critic preview content. |
| `backend/api/routes/runs.py` | in-repo seam | Assembles run detail plus transparency summary for the frontend | Existing route path can surface new narrative preview fields without inventing a separate endpoint. |
| `frontend/src/lib/run-primary-view.ts` | in-repo seam | Normalizes run and transparency data into the chat or answer view model | Already owns answer derivation and fallback logic, so it is the right migration seam. |
| `frontend/src/components/chat-shell/chat-run-answer-card.tsx` | in-repo seam | Primary narrative reading surface inside chat | Current component already owns the centered answer rendering and can be reshaped around prose. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `frontend/src/actions/runs.ts` | in-repo seam | Return the narrative answer for new chat-triggered runs | Use to ensure live replies and persisted history consume the same answer contract. |
| `frontend/src/lib/chat-run-history.ts` | in-repo seam | Reconstruct persisted run history into chat messages | Use to preserve history compatibility while rolling out the new narrative fields. |
| `frontend/src/lib/api/types.ts` | in-repo seam | Frontend wire types for transparency payloads | Extend when adding new backend-safe narrative preview fields. |
| `tests/test_run_transparency_builders.py` and `tests/test_sprint3_transparency_api.py` | in-repo seam | Backend regression anchors for safe preview contracts | Use to lock the new preview fields into the trusted run-transparency surface. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Add backend-authored narrative preview fields | Assemble long-form prose in the frontend from existing takeaways and caveats | Faster to prototype, but brittle, repetitive, and less auditable. |
| Additive migration from `summaryLine` to narrative fields | Hard replace the summary-era contract everywhere at once | Cleaner in theory, but much riskier for persisted history, live replies, and test coverage. |
| Partial-answer narrative fallback | Hide the answer body when support is limited | Safest mechanically, but too empty for the product direction and fails the chat-reader goal. |
| Narrative-first rendering with old fields preserved for compatibility | Leave takeaway cards as the main body and simply lengthen the summary text | Lowest effort, but it would not actually change the product architecture. |

## Recommended Patterns

### Pattern 1: Add a Backend-Safe Narrative Preview Layer

**What:** Extend `RunTransparencySummary` with explicit narrative preview fields rather than forcing the frontend to infer a narrative from fragments.

**When to use:** Any chat-visible answer surface that should remain inside the existing safe-preview trust boundary.

**Why:** The backend already exposes preview-safe report and critic slices. The narrative answer should use the same seam so the browser does not need raw artifacts or ad hoc prose synthesis.

**Recommended field shape:**
- `answer_thesis_preview`
- `answer_support_preview`
- `answer_watchouts_preview`
- `answer_fallback_mode` or equivalent explicit limitation marker

The exact names can vary, but the structure should make thesis, support, and weakening context first-class.

### Pattern 2: Keep `run-primary-view` as the Derivation Hub

**What:** Continue using `frontend/src/lib/run-primary-view.ts` as the canonical answer builder, but make it prefer narrative fields over `summaryLine`.

**When to use:** Live chat replies, hydrated run history, and any future trace-linked preview surfaces that need the same answer semantics.

**Why:** This file already:
- normalizes generic-success summaries
- resolves fallback behavior
- adapts run and transparency data into chat-card-ready structures

Migrating here keeps the product from splitting into two answer languages.

### Pattern 3: Migrate Additively, Not by Hard Cutover

**What:** Introduce narrative fields and derive them first, while preserving summary-era fields as compatibility fallback for older or sparse runs.

**When to use:** The first release of the narrative contract.

**Why:** Persisted history and older runs may not have the new narrative preview fields immediately. Additive migration allows:
- older runs to remain readable
- new runs to render the richer contract
- tests to prove both paths stay coherent

### Pattern 4: Treat Weak-Support Answers as Partial Narratives

**What:** Use the same prose contract for both full and limited-support answers, but make the watchouts or limitation paragraph explicit when evidence is thin.

**When to use:** Runs with weak coverage, insufficient peer context, missing artifacts, or critic/report signals that do not support a strong thesis.

**Why:** This avoids both extremes:
- blank answer surfaces
- overconfident prose not supported by evidence

The user still gets a readable reply, but the answer explicitly names what cannot be concluded.

### Pattern 5: Keep Findings and Evidence Secondary for This Phase

**What:** Let the narrative body carry the main reading load in Phase 17; do not solve supplemental evidence disclosure or charts here.

**When to use:** Every planning and implementation decision for this phase.

**Why:** Later phases already own:
- confidence explainer
- evidence disclosure redesign
- inline charts

If Phase 17 pulls those concerns forward, the answer contract will sprawl before the narrative core is stable.

## Implementation Slices

### Slice A: Backend Narrative Preview Contract

Focus files:
- `backend/schemas/run_transparency.py`
- `backend/api/routes/runs.py`
- `frontend/src/lib/api/types.ts`
- `tests/test_run_transparency_builders.py`
- `tests/test_sprint3_transparency_api.py`

Deliver:
- new safe narrative preview fields on the run transparency surface
- API and frontend typing updates
- backend regression coverage for narrative preview construction

### Slice B: Frontend Answer Builder Migration

Focus files:
- `frontend/src/lib/run-primary-view.ts`
- `frontend/src/lib/__tests__/run-primary-view.test.ts`
- `frontend/src/actions/runs.ts`
- `frontend/src/lib/chat-run-history.ts`
- related tests

Deliver:
- narrative-first answer view derivation
- additive fallback behavior for older or sparse runs
- consistent live-reply and persisted-history rendering semantics

### Slice C: Chat Renderer and Compatibility Hardening

Focus files:
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`

Deliver:
- narrative prose as the primary visible payload
- summary-era placeholders removed from the main reading path
- regression coverage for full narrative and partial-answer fallback cases

## Validation Architecture

Phase 17 touches both backend-safe preview contracts and frontend answer rendering, so validation needs a mixed Python + Vitest gate.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx
```

**Recommended full command:**
```bash
python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/lib/chat-run-history.test.ts src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build
```

**Required new or expanded tests:**
- `tests/test_run_transparency_builders.py`
  - narrative preview fields are populated from traceability-safe report or critic slices
  - sparse inputs preserve explicit fallback-safe outputs instead of silently dropping to empty strings
- `tests/test_sprint3_transparency_api.py`
  - run detail API exposes the new narrative preview fields when `include_transparency=true`
- `frontend/src/lib/__tests__/run-primary-view.test.ts`
  - narrative preview fields are preferred over `summaryLine`
  - generic-success summaries no longer dominate the main answer path
  - partial-answer fallback is explicit when support is limited
- `frontend/src/actions/runs.test.ts` and `frontend/src/lib/chat-run-history.test.ts`
  - live replies and hydrated history use the same narrative-first contract
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
  - the chat renderer shows narrative prose as the main payload and keeps fallback answers readable

## Pitfalls and Boundaries

- Do not build the narrative body entirely in the browser from takeaway fragments.
- Do not break persisted history for older runs that only have summary-era preview data.
- Do not treat the first finding card as a sufficient substitute for a narrative answer.
- Do not collapse weak-support cases into generic “completed successfully” copy.
- Do not pull confidence-explainer, evidence-disclosure, or chart logic into this phase.

## Recommended Plan Shape

Phase 17 should be planned as **3 sequential plans**:

1. **Backend narrative preview contract** — extend safe transparency fields and API typing to carry thesis, support, and watchouts or fallback context
2. **Frontend answer-builder migration** — make the answer model narrative-first while preserving compatibility with summary-era runs
3. **Chat rendering and fallback hardening** — render the longer narrative answer cleanly in chat and lock down partial-answer behavior with regressions

That sequence satisfies `ANSR-01` and `ANSR-02` while keeping the evidence, confidence, and chart architecture in their later dedicated phases.

## Sources
- `.planning/phases/17-narrative-answer-contract/17-CONTEXT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `backend/schemas/run_transparency.py`
- `backend/api/routes/runs.py`
- `frontend/src/lib/run-primary-view.ts`
- `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
- `frontend/src/actions/runs.ts`
- `frontend/src/lib/chat-run-history.ts`
