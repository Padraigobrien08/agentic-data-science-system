---
phase: 21
slug: narrative-answer-polish
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-25
---

# Phase 21 - UI Design Contract

> Finish the narrative answer experience so it feels like one centered, editorial chat reply with subordinate proof and a clearly technical trace surface.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` |
| Component library | radix |
| Icon library | lucide |
| Font | inherit the shipped `v1.3` answer stack; keep the current `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif` family and avoid adding a new display type system |

Source: aligned to `frontend/components.json`, current answer shell components, and the locked decisions from Phases 17-20.

## Visual Hierarchy

**Primary focal point:** the narrative answer prose.

**Secondary focal points:**
1. the confidence pill inside the answer header
2. optional inline chart cards
3. the supporting-evidence disclosure

**Tertiary focal points:**
1. the secondary navigation pills
2. trace/open-source escape hatches

Rules:

- The answer should read like one editorial reply, not a stack of independent widgets.
- The eye should move down the answer in this order: thesis, prose body, confidence rider if present, charts if present, supporting evidence disclosure, then secondary navigation.
- The answer column should remain centered on desktop and roomy without feeling card-stacked.
- On smaller screens, relax the centered column into a near-full-width reading surface with modest safe margins.
- Do not reintroduce side rails, competing columns, or heavy chrome.

## Spacing Scale

Reuse the existing 4-point rhythm, but simplify the answer shell into calmer section spacing.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | inline label offsets, icon gaps, tiny utility spacing |
| sm | 8px | small support-note spacing, pill gaps |
| md | 16px | paragraph adjacency, disclosure internals, chart caption spacing |
| lg | 24px | section-to-section rhythm within the answer shell |
| xl | 32px | desktop breathing room between major answer zones |
| 2xl | 48px | transcript-level separation between messages only |

Rules:
- The thesis-to-body transition should feel intentional, not collapsed.
- Narrative sub-sections should use `md` to `lg` rhythm, not separate card blocks.
- Charts and disclosure should have `lg` separation from the prose body.
- Secondary navigation should sit close enough to feel connected, but quiet enough not to compete.

## Typography

Keep the current restrained type system and reduce utility-label noise.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Display | 20px-22px | 600 | 1.45 |
| Body | 15px-16px | 400 | 1.75 |
| Utility | 12px-13px | 400 | 1.55 |
| Overline | 10px | 600 | 1.2 |

Rules:
- The answer thesis should remain the strongest text treatment, but not feel like a landing-page hero.
- Narrative section overlines must stay quiet and consistent; do not let utility labels dominate the answer.
- Inline source links should inherit body rhythm and feel like precise citations, not loud CTAs.
- Trace headings can be denser and more technical, but should not outshine the answer styling.

## Color

Stay inside the shipped light workspace palette.

| Role | Value | Usage |
|------|-------|-------|
| Background | `#f5f7fb` / `hsl(var(--ui-background))` | transcript field and page backdrop |
| Surface | `#ffffff` / `hsl(var(--ui-card))` | answer shell, disclosure, chart card, trace cards |
| Accent | existing blue `#1f6fff` | exact source links, active nav affordances, selected technical actions |
| Semantic | keep existing `Good / Medium / Bad / Not rated` confidence mapping | confidence pill only |

Rules:
- Do not add another highlight color family for prose polish.
- Source links should feel crisp and exact, not primary CTA-like.
- Chart colors remain governed by the existing chart token mapping from Phase 20.
- Trace should remain slightly denser and more neutral than chat, not brighter.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Answer overline | `Answer` |
| Supplemental disclosure | `Show supporting evidence` / `Hide supporting evidence` |
| Secondary pills | preserve existing labels |
| Trace back-link copy | prefer `Back to chat` or `Return to answer` |
| Trace framing copy | use `technical deep dive`, `inspect`, `audit`, or `technical surface` |

Rules:
- Chat copy should sound like an analyst answer, not a product tour.
- Trace copy should sound like inspection/audit language, not like a second answer reader.
- Inline links should read like precise citations: short, calm, and literal.

## Component Contract

### Answer shell

- Keep `ChatRunAnswerCard` as one centered reading surface.
- Reduce the feeling of stacked sections by using quieter separators and more editorial rhythm.
- Narrative sections should feel like one continuous answer with light structure, not detached utility modules.

### Inline citations / source links

- Render source links only where they sharpen a claim or offer a natural jump.
- Keep them inline or immediately adjacent to the claim they support.
- Avoid repeating `Open source` links so aggressively that they dominate the reading flow.

### Responsive behavior

- Desktop:
  - keep a centered column
  - allow generous reading width without stretching prose too far
- Tablet:
  - reduce outer margins
  - keep charts/disclosure fully stacked
- Mobile:
  - near-full-width answer surface with modest padding
  - confidence pill, charts, disclosure, and pills remain in one vertical stack

### Trace wording and navigation

- Trace summary should clearly state that it exists for technical audit and inspection.
- Buttons and helper copy should direct the user back to chat for the answer-reading experience.
- Avoid language that implies trace is where the “real answer” lives.

## Interaction Contract

- No new interactions are introduced in this phase.
- Disclosure, popover, and chart interactions remain as already shipped.
- This phase only clarifies rhythm, alignment, responsive behavior, and wording.

## State Contract

| State | Visual Contract | Copy Contract |
|------|-----------------|---------------|
| Full answer | centered editorial reply with subordinate proof layers | calm analyst-memo voice |
| Partial answer | same hierarchy, with one short caution rider | clear but not alarmist |
| Error answer | still centered and readable, but visibly non-success | direct next-step wording |
| Charted answer | charts stay subordinate to prose | captions and links remain precise |
| Limited evidence | disclosure still present, quiet and explicit | confirms support was checked but is thin |

## Phase Boundaries

- Do not add new backend fields.
- Do not redesign confidence semantics.
- Do not redesign disclosure semantics.
- Do not expand chart controls.
- Do not add a new answer surface parallel to chat.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | existing local shadcn primitives only | official-only registry, no additional vetting required - 2026-04-25 |
| third-party | none | not applicable - 2026-04-25 |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved
