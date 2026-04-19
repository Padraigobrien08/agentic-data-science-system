---
phase: 15
slug: evidence-navigation-in-chat
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-19
reviewed_at: 2026-04-19T11:25:00Z
---

# Phase 15 — UI Design Contract

> Visual and interaction contract for inline findings, confidence, caveats, and compact evidence navigation in the chat-native answer.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` |
| Component library | radix |
| Icon library | lucide |
| Font | inherit Phase 14 stack: `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`; display accents `"Iowan Old Style", "Palatino Linotype", serif`; `ui-monospace` for run ids and technical metadata |

## Visual Hierarchy

**Primary focal point:** the assistant answer summary at the top of the chat card.

**Secondary focal points:**
1. top findings
2. confidence and caveats
3. compact evidence navigation
4. run identity strip

**Rules:**

- Keep the card as one coherent reading surface, not stacked unrelated boxes.
- Findings, caveats, and navigation must read as layers of the same answer, not as separate mini-pages.
- The evidence navigation area must be visually calmer than the conclusion and findings.
- Secondary verification links should never dominate the reading flow.

## Spacing Scale

Use the Phase 14 spacing scale unchanged:

- `xs` 4px
- `sm` 8px
- `md` 16px
- `lg` 24px
- `xl` 32px

Additional density rules:

- finding rows use `sm` vertical rhythm
- section breaks inside the answer card use `md` to `lg`
- the compact navigation surface should fit within one card section without creating a new full-width footer slab

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 | 1.5 |
| Label | 10px | 600 | 1.2 |
| Heading | 16px | 600 | 1.25 |
| Meta | 12px | 400/600 | 1.4 |

Rules:

- findings should remain body-sized, not heading-sized
- caveat badges stay micro and compact
- compact nav labels should read as utility navigation, not primary CTAs

## Color

Reuse the Phase 14 palette and keep accent discipline.

- Accent blue remains reserved for the one primary run action and focus state.
- Findings and navigation links should use neutral or foreground treatments first.
- Warning tones may highlight caveats, but do not wash the entire card in alert styling.
- Navigation chips or tabs should not become colorful badges unless their meaning depends on tone.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Findings heading | `Top findings` |
| Confidence heading | `Confidence & caveats` |
| Navigation heading | `Open evidence` |
| Compact nav labels | `Report`, `Evidence`, `Artifacts`, `Critic`, `Trace` |
| Exact jump affordance | `Open source` or similarly quiet secondary phrasing |

Rules:

- avoid jargon-heavy labels like `artifact surfaces`
- navigation text should be short and operator-readable
- caveat copy stays concise and traceable, not conversational

## Component Contract

### Chat answer card

The card now contains, in order:

1. conclusion
2. conclusion rider when present
3. goal
4. optional orchestration disclosure
5. top findings section
6. confidence and caveats section
7. compact evidence navigation section
8. run identity strip

### Top findings

- Show takeaway rows first.
- Alignment or critic findings follow as secondary cards.
- Do not repeat the full multi-chip row under every item as the dominant pattern.
- If item-level evidence jumps are present, they should be quiet secondary links or one compact affordance per row.

### Confidence & caveats

- Show one compact confidence strip.
- Show bounded caveat/context badges.
- Blocking caveats may expand into a short list, but overflow routes to trace or deep dive.

### Compact evidence navigation

- One unified area with access to report, evidence, artifacts, critic, and trace.
- Can be a segmented row, pill row, or compact stack, but must read as one navigation surface.
- Avoid repeating large outlined buttons.

### Run strip

- Keep the Phase 14 run strip intact.
- It remains the final section in the card.

## Interaction Contract

- The chat answer should let a user read and do first-pass verification without leaving chat.
- Item-level exact jumps must target the relevant artifact or trace anchor directly.
- Navigation actions should open the existing secondary surfaces; no new modal or drawer in this phase.
- If a section has nothing useful yet, prefer concise empty copy rather than removing structural consistency.

## State Contract

| State | Contract |
|-------|----------|
| Success | All sections may render if data exists, with bounded density |
| Partial / no data | Findings and nav can render sparse states without collapsing the card structure |
| Error | Phase 14 compact error card remains; do not pull Phase 15 evidence surfaces into failed runs |
| Pending | Phase 14 pending shell remains bounded; no fake findings or evidence placeholders beyond light structural hints |

## Phase Boundaries

- Do not simplify the standalone run page here.
- Do not embed markdown reports or raw trace payloads inside chat.
- Do not create multi-pane chat layouts, drawers, or tabbed inspectors.
- Do not turn chat into a generic dashboard of every artifact.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `card`, `button`, `badge`, `separator` | not required |
| third-party | none | not applicable |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-04-19
