# Phase 19: Supplemental Evidence Disclosure - Research

**Researched:** 2026-04-24  
**Domain:** Narrative-first chat answers with clearly secondary supporting evidence  
**Confidence:** MEDIUM

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

### Disclosure behavior
- **D-01:** Supplemental evidence should be collapsed by default.
- **D-02:** The answer should expose one clear `Show supporting evidence` disclosure beneath the narrative answer.
- **D-03:** The answer must remain the default reading path.

### Evidence card shape
- **D-04:** Evidence rows inside the disclosure should be long and slim.
- **D-05:** Each row should contain a short title, one “why it matters” sentence, and one exact jump link.
- **D-06:** The layout should make better use of horizontal chat width than the current stacked cards.

### Disclosure contents
- **D-07:** Current takeaway rows and alignment/finding cards should merge into one unified supplemental evidence list.
- **D-08:** Phase 19 should remove the split between separate support subsections on the chat answer path.
- **D-09:** The disclosure should feel like one proof layer, not multiple competing support zones.

### Secondary navigation placement
- **D-10:** Keep `Report / Evidence / Artifacts / Critic / Trace` below the disclosure.
- **D-11:** Keep those pills always visible but visually secondary.
- **D-12:** Do not move the pills into the answer header or bury them inside the disclosure.

### Thin or missing evidence behavior
- **D-13:** Keep the disclosure present even when evidence is weak or sparse.
- **D-14:** Opening it in thin-evidence cases should reveal a compact limited-evidence or empty-evidence state.
- **D-15:** The product should clearly communicate “we checked, but support is limited.”

### the agent's Discretion
- Exact disclosure label copy and chevron treatment
- Exact merged evidence-row component shape
- Exact limited-evidence empty-state copy

### Deferred Ideas (OUT OF SCOPE)
- Deterministic inline charts in chat — Phase 20
- Final narrative/evidence responsive polish — Phase 21
- Remembered disclosure state per user/workspace
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ANSR-03 | User can treat the narrative answer as the primary reading surface, with findings and supporting detail clearly subordinate to it | Collapse the current always-visible support area behind a disclosure so the answer body remains visually dominant. |
| EVID-01 | User can expand or collapse supplemental evidence beneath the narrative answer instead of reading evidence cards as the primary response | Add one explicit disclosure boundary in the chat answer card rather than leaving support permanently open. |
| EVID-02 | User can scan slim supporting evidence cards that explain why each source matters and jump directly to the relevant artifact or trace target | Replace the current stacked finding/takeaway treatments with one unified slim evidence-row model. |
| EVID-03 | User can still access report, evidence, artifacts, critic output, and trace through one compact secondary navigation strip below the supplemental evidence section | Keep current `navigationItems` as the secondary navigation layer, but reposition them beneath the disclosure. |
</phase_requirements>

## Summary

The current Phase 18 answer card already has the right high-level hierarchy at the top: narrative answer first, confidence in the header, and only one short rider beneath the prose. The remaining problem is the lower half of the card. `ChatRunAnswerCard` still renders a permanently open `Supporting detail` section whenever `takeawayRows` or `alignmentFindings` exist, followed by an always-visible `Evidence` strip with the five pills. That means the card still reads like “answer plus support panel” rather than “answer first, proof on demand.”

The cleanest Phase 19 move is not to add new evidence data sources. The repo already has the right data seam in `frontend/src/lib/run-primary-view.ts`: `takeawayRows`, `alignmentFindings`, `navigationItems`, `evidenceProvenanceHint`, and the limited-evidence signals are already derived in one place. The missing piece is a unified presentation model. Right now `takeawayRows` and `alignmentFindings` are rendered by two different components with different card shapes and different information density. Research points to merging them into one supplemental evidence list with a shared row contract: short title, one-sentence why-it-matters text, and one exact jump link.

That unified list should sit behind one disclosure in `ChatRunAnswerCard`, collapsed by default. When evidence is thin, the disclosure should remain present but open to a compact empty or limited-support state driven by existing hints such as `emptyStateReason`, `evidenceProvenanceHint`, `weakEvidenceSignals`, and low evidence-link counts. This is important because hiding the disclosure entirely would make users unsure whether support was absent or simply failed to render. The disclosure therefore becomes the place where the product says “here is the proof layer” or “here is why the proof layer is thin.”

The current `navigationItems` seam is already close to what Phase 19 needs. Those five pills should remain below the disclosure as the persistent secondary escape hatch rather than being moved into the disclosure or promoted into the answer header. That preserves direct navigation to artifacts and trace without letting the pills dominate the primary reading path.

**Primary recommendation:** keep the existing view-model seam, add one disclosure wrapper in the chat answer card, introduce a unified slim evidence-row component that absorbs both takeaway and alignment content, and keep the five pills below the disclosure as a secondary strip.

## Project Constraints (from AGENTS.md / PROJECT.md)

- Keep the existing Python + FastAPI + SQLAlchemy + Next.js architecture; this phase should stay in the frontend/view-model layer rather than inventing a new backend evidence API.
- Preserve the deterministic analysis core in `src/`; evidence disclosure is presentation work over already-derived trusted artifacts and traceability.
- Prefer explicit seams and incremental migration over invasive refactors; reuse `run-primary-view.ts`, `chat-run-answer-card.tsx`, and existing evidence/navigation models.
- Keep UI data access server-side and typed; the browser should consume typed run/transparency data, not parse raw payloads ad hoc.
- Do not break existing artifact URLs, trace anchors, or chat history hydration while reorganizing the evidence presentation.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Next.js App Router | `^15.1.0` | Keep chat run hydration and navigation server-backed | Existing chat history and run fetch paths already use this model. |
| React | `^19.0.0` | Render the disclosure, merged evidence rows, and persistent pill strip | The chat answer surface is already a client-side component tree fed by typed props. |
| shadcn/ui local patterns | repo-local | Reuse the same local component style as the confidence pill/disclosure work | The milestone direction already prefers shadcn-style primitives and composable local UI pieces. |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Vitest | `^2.1.9` | Renderer and view-model regressions | When changing `run-primary-view`, `ChatRunAnswerCard`, or disclosure behavior. |
| Existing structured-answer components | current repo | Transitional reuse while the evidence rows are being unified | Use as a source of current copy, chip behavior, and exact-jump semantics. |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| One collapsed disclosure | Keep support always open and just restyle it | Lower effort, but it fails the answer-first requirement. |
| Unified slim evidence rows | Preserve separate `TopFindingsList` and `FindingCards` sections inside the disclosure | Easier migration, but keeps the current fragmented proof model. |
| Pills below the disclosure | Put pills inside the disclosure footer | Cleaner collapsed state, but hides important escape hatches. |

## Architecture Patterns

### Recommended Project Structure
```text
frontend/src/
├── components/chat-shell/
│   └── chat-run-answer-card.tsx         # disclosure boundary + answer hierarchy
├── components/structured-answer/
│   ├── supplemental-evidence-row.tsx    # likely new slim merged evidence row
│   ├── top-findings-list.tsx            # candidate migration source / compatibility path
│   ├── finding-cards.tsx                # candidate migration source / compatibility path
│   └── evidence-summary.tsx             # persistent secondary pill strip
└── lib/
    └── run-primary-view.ts              # unify takeaway/alignment content into one supplemental evidence list
```

## Validation Architecture

Phase 19 is primarily a frontend hierarchy and renderer phase. The most important validations are:
- view-model tests proving current takeaway/alignment content is merged into one supplemental evidence list
- chat renderer tests proving the disclosure is collapsed by default
- chat renderer tests proving the disclosure still shows a limited-evidence state when support is thin
- build coverage proving the new disclosure and row component integrate cleanly with the existing chat shell

## Pattern 1: One Disclosure Boundary, Not Multiple Support Sections
**What:** Use one explicit disclosure beneath the answer for all supplemental evidence.

**When to use:** The primary chat answer card.

**Why:** This is the simplest way to make the narrative answer the main reading surface while still preserving verifiability on demand.

## Pattern 2: Unified Supplemental Evidence Row Model
**What:** Normalize takeaway and alignment content into one row shape with:
- `title`
- `why_it_matters`
- `jump`

**When to use:** Any supporting evidence shown in the disclosure.

**Why:** The current split between takeaways and alignment cards is a presentation artifact, not a user need. One unified row model will read more cleanly and use the available width better.

## Pattern 3: Persistent Secondary Navigation Outside the Disclosure
**What:** Keep `Report / Evidence / Artifacts / Critic / Trace` visible below the disclosure rather than hiding them inside it.

**When to use:** The lower edge of the chat answer card.

**Why:** These are escape hatches, not evidence rows. They should stay available even when the disclosure is closed.

## Pattern 4: Limited-Evidence State Inside the Same Disclosure
**What:** When support is thin, the disclosure should still open to a compact explanatory state rather than disappearing.

**When to use:** Runs with sparse evidence links, low extracted support, or explicit limited-evidence signals.

**Why:** This keeps the proof layer honest and discoverable without implying that the system forgot to load it.

## Anti-Patterns to Avoid

- **Always-visible support panel:** Re-styling the current support area without collapsing it still leaves evidence competing with the answer.
- **Two different supplemental models:** Do not keep separate `takeaways` and `findings` sections once the disclosure exists.
- **Header pill sprawl:** Do not move the five pills into the answer header; that would undo the cleanup from Phase 18.
- **Missing-evidence invisibility:** Do not hide the disclosure entirely when evidence is weak.

## Common Pitfalls

### Pitfall 1: The Disclosure Still Feels Like a Sectioned Dashboard
**What goes wrong:** The disclosure opens to multiple labeled subsections and the answer still feels buried above a mini-control panel.  
**How to avoid:** Use one merged evidence list and keep the pills visually distinct as a separate secondary strip below.

### Pitfall 2: Slim Rows Lose Why-the-Evidence-Matters Context
**What goes wrong:** Rows become too terse and read like filenames or labels with no analytical meaning.  
**How to avoid:** Keep one sentence of “why it matters” in every row, even if titles are short.

### Pitfall 3: Empty Evidence Looks Like a Rendering Failure
**What goes wrong:** Users open the disclosure and see nothing, or the disclosure disappears completely.  
**How to avoid:** Always render a compact limited-evidence or empty-evidence state with explicit copy.
