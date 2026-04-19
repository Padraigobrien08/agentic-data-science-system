---
phase: 17
slug: narrative-answer-contract
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-19
reviewed_at: 2026-04-19T22:50:00Z
---

# Phase 17 — UI Design Contract

> Visual and interaction contract for turning the chat answer from a summary card into a narrative analyst reply.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` |
| Component library | radix |
| Icon library | lucide |
| Font | inherit Phase 14/15 stack: `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`; restrained serif emphasis only for rare display moments, not for body prose |

Source: aligned to the initialized `frontend/components.json`, existing globals, and the currently shipped chat answer shell.

## Visual Hierarchy

**Primary focal point:** the assistant answer body itself.

**Reading order:**
1. answer label and thesis
2. narrative prose body
3. light limitation or watchout rider
4. subordinate findings/supporting structure that still exists in Phase 17

**Rules:**

- The assistant response must read like one centered editorial answer surface, not a dashboard.
- The prose column is the main event; utility structure must visually step back.
- Remove the current feeling of “headline on the left, support UI everywhere else.”
- Avoid a prominent two-column split for this phase. The answer should sit in one centered reading column on desktop and mobile.
- The user bubble can remain offset, but the assistant answer should feel anchored to the center of the conversation space, closer to a ChatGPT-style reading flow than to a metrics panel.

## Spacing Scale

Use the existing 4-point rhythm, but bias toward calmer narrative spacing:

| Token | Value | Usage |
|------|------|--------|
| xs | 4px | inline separators, microcopy gaps |
| sm | 8px | label-to-body spacing, pill gaps |
| md | 16px | paragraph spacing, inner card padding on mobile |
| lg | 24px | section spacing within the answer card |
| xl | 32px | desktop answer-card padding, transcript breathing room |
| 2xl | 48px | large transcript separation only |

Rules:
- narrative paragraphs use `md` vertical rhythm
- header-to-body spacing should feel tighter than the current card-section separations
- avoid giant section slabs or boxed subsections in the main prose flow

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.7 |
| Label | 10px | 600 | 1.2 |
| Heading | 18px | 600 | 1.35 |
| Display / Thesis | 20px | 600 | 1.5 |

Rules:
- the thesis should read as strong editorial body text, not as a giant hero headline
- prose sections should be body-sized and comfortable to read across a centered column
- labels remain compact and quiet
- avoid dense miniature text for the primary answer

## Color

Reuse the existing neutral workspace palette and keep accent usage narrow.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `hsl(var(--ui-background))` / current workspace canvas | Transcript background and page field |
| Secondary (30%) | `hsl(var(--ui-card))` / current card surface | Assistant answer card and subordinate blocks |
| Accent (10%) | `hsl(var(--ui-primary))` / current blue | Focus state, single primary action only |
| Destructive | `hsl(var(--ui-destructive))` | Error states only |

Rules:
- do not use accent blue to decorate the narrative answer body
- the primary prose should rely on foreground and muted tones, not colored emphasis
- supporting UI can use borders, surface shifts, and muted labels before color

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary heading label | `Answer` |
| Narrative section labels | `What’s happening`, `Why we think that`, `What weakens the claim` |
| Fallback limitation lead | direct statement of what is supported and what is missing |
| Empty or weak-support posture | never generic success text; always explain the limitation concretely |
| Primary CTA | none added in this phase beyond existing secondary navigation affordances |

Rules:
- answer prose must read like an analyst memo, not a chatbot
- avoid “Here’s what I found” or other assistant framing
- avoid process-language headlines like `Run completed successfully`

## Component Contract

### Assistant answer card

The answer card should shift from a sectioned utility layout to a narrative reading layout:

1. quiet `Answer` label
2. thesis line
3. 2-3 narrative prose blocks
4. optional short limitation rider
5. existing subordinate support surfaces only if still needed for compatibility

### Layout contract

- On desktop, center the assistant answer within a readable max width of roughly `46rem` to `54rem`.
- Do not use the current dominant left-content/right-rail split for the main answer.
- If legacy support blocks remain during migration, they must sit below the prose, not beside it.

### Transitional compatibility

- Phase 17 may still temporarily reuse some findings/supporting blocks from the previous answer card implementation.
- Those blocks must be visually subordinate to the narrative body:
  - smaller heading weight
  - reduced surface contrast
  - placed below the prose, not above or beside it

## Interaction Contract

- The user should be able to read the main answer without needing to expand, click, or inspect anything else.
- The main answer should feel complete enough on its own before later evidence phases arrive.
- Fallback answers must preserve the same narrative footprint as full answers, even if shorter.
- Do not introduce new modal, drawer, or disclosure behavior in this phase.

## State Contract

| State | Visual Contract | Copy Contract |
|------|-----------------|---------------|
| Success | Centered narrative answer with thesis + prose sections | concrete analyst prose |
| Partial | Same narrative footprint, but shorter and more explicit about evidence limits | strongest supportable claim plus limitation statement |
| Weak or sparse | No blank cards, no generic success line, no mirrored card fragments as the main payload | say what is missing or weak |
| Error | Reuse the same centered answer shell, but with a concise failure block instead of narrative prose | `This analysis didn’t finish cleanly.` followed by `Open trace to inspect what failed, then retry with narrower wording or refreshed SEC data.` |
| Pending | Existing pending shell may remain, but it should foreshadow a centered narrative answer rather than a dashboard card | `Running analysis...` / `Updating…` remains acceptable |

## Phase Boundaries

- Do not add inline confidence badge or explainer here.
- Do not move evidence into a disclosure system here.
- Do not add charts here.
- Do not redesign the entire chat shell or sidebar here.
- Do not turn the answer into a long-scroll report; keep it concise and centered.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | existing `card`, `separator`, `badge`, `button` surfaces only | not required |
| third-party | none | not applicable |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-04-19
