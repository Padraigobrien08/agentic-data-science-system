---
phase: 19
slug: supplemental-evidence-disclosure
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-24
reviewed_at: 2026-04-24T22:30:00Z
---

# Phase 19 — UI Design Contract

> Visual and interaction contract for making evidence clearly supplemental to the narrative answer instead of permanently sharing the stage with it.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` |
| Component library | radix |
| Icon library | lucide |
| Font | inherit Phase 17/18 stack: `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`; no new display-font shift in this phase |

Source: aligned to the shipped Phase 17 centered narrative answer surface, Phase 18 confidence header, and current chat answer shell.

## Visual Hierarchy

**Primary focal point:** the narrative answer body.

**Secondary focal point:** the confidence pill in the answer header.

**Tertiary focal points:**
1. one explicit `Show supporting evidence` disclosure
2. slim supporting evidence rows only after disclosure opens
3. persistent secondary navigation pills beneath the disclosure

**Rules:**

- Evidence must read as proof on demand, not as the answer itself.
- The closed answer state should feel complete and calm before any evidence is opened.
- The disclosure affordance should be obvious, but it must not visually outweigh the narrative answer.
- Once opened, evidence should still feel lightweight and horizontal, not like a second dashboard below the answer.
- Do not preserve separate visual zones for `takeaways` and `findings`; the proof layer should feel singular.

## Spacing Scale

Reuse the current 4-point rhythm and bias toward a compact disclosure transition:

| Token | Value | Usage |
|------|------|--------|
| xs | 4px | chevron gaps, micro-separators, inline source spacing |
| sm | 8px | evidence row internals, disclosure trigger padding, pill gaps |
| md | 16px | standard card padding, row vertical rhythm, disclosure body spacing |
| lg | 24px | separation between answer body and disclosure area |
| xl | 32px | answer-card breathing room on desktop |

Rules:
- The closed disclosure should sit close enough to the answer to feel related, but not so close that it reads like another paragraph.
- Open evidence rows should use `md` rhythm vertically and generous horizontal space.
- The five secondary pills should feel tighter and lighter than the evidence rows above them.
- Avoid stacked slabs of large padding; Phase 19 should reduce visual heaviness, not increase it.

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.7 |
| Label | 10px | 600 | 1.2 |
| Heading | 18px | 600 | 1.35 |
| Disclosure trigger | 13px | 500 | 1.35 |
| Evidence row title | 13px | 600 | 1.35 |
| Evidence row reason | 13px | 400 | 1.5 |
| Secondary pill text | 11px | 500 | 1.2 |

Rules:
- The narrative answer stays editorial and dominant.
- Evidence rows should read like support notes, not mini-headlines.
- The disclosure trigger should sound confident and readable, but quieter than the answer thesis.
- Do not introduce monospace or technical-label typography into the primary chat surface.

## Color

Reuse the existing workspace neutrals and Phase 18 semantic confidence treatment.

| Role | Value | Usage |
|------|-------|-------|
| Dominant | existing canvas / transcript neutrals | chat background, answer field |
| Secondary | existing card neutrals | answer card, disclosure panel, evidence rows |
| Accent | existing blue reserved sparingly | only exact jump links and the single active disclosure affordance when open |
| Destructive | existing destructive token | only error or failed-evidence states if needed |

Rules:
- Do not color the evidence section as a separate themed zone.
- Evidence rows should rely on subtle surface contrast and border definition rather than heavy accent color.
- Secondary pills stay neutral and subdued.
- The disclosure trigger may use a subtle active/open state, but it must not look like a primary CTA.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Disclosure closed label | `Show supporting evidence` |
| Disclosure open label | `Hide supporting evidence` |
| Evidence row source jump | `Open source` |
| Thin-evidence heading | `Supporting evidence is limited` |
| Thin-evidence body | concise explanation of what was checked and what support is missing |
| Empty-evidence body | concise explanation that artifacts or mapped support were not available for this answer view |

Rules:
- Evidence copy should sound like support for the answer, not like a separate report.
- Avoid technical labels such as `alignment finding`, `takeaway`, or `evidence summary` in the visible chat surface.
- The disclosure label should be direct and calm, not playful or dashboard-like.
- Thin-evidence copy must explain the limitation clearly instead of implying a rendering failure.

## Component Contract

### Disclosure boundary

- Use one disclosure directly beneath the narrative answer and any short rider.
- Closed state shows only the label row with chevron.
- Open state reveals one merged evidence list.
- The disclosure remains present even when support is weak or sparse.

### Evidence rows

Each row should be long and slim, with this order:

1. short evidence title
2. one sentence explaining why it matters
3. one exact jump link

Rules:
- One row should fit comfortably across the main answer column on desktop.
- Do not use tall stacked cards with multiple chip groups.
- Keep row chrome light: rounded edge, thin border, subtle fill, no heavy card shadow.
- Rows may wrap on mobile, but should still feel like condensed support notes rather than large cards.

### Merged evidence model

- The disclosure should present one unified support list.
- Former `takeaway` and `alignment` concepts may still exist in code, but they must not appear as separate user-facing sections here.
- Ordering should favor the strongest or most explanatory support first.

### Secondary pills

- Keep `Report`, `Evidence`, `Artifacts`, `Critic`, and `Trace` below the disclosure.
- They remain visible whether the disclosure is open or closed.
- They must be visually secondary: smaller, quieter, and clearly navigational rather than explanatory.

### Thin-evidence state

- If the support layer is thin, the disclosure still opens.
- The open state should show compact explanatory copy and any still-available exact jumps.
- Do not collapse to an empty white space.

## Interaction Contract

- The user should understand the answer without opening the disclosure.
- Opening the disclosure should feel like asking for proof, not switching modes.
- Disclosure open/close behavior should be instant and local to the answer card.
- The five pills must remain usable regardless of disclosure state.
- Keyboard and screen-reader interaction must preserve clear disclosure semantics.

## State Contract

| State | Visual Contract | Copy Contract |
|------|-----------------|---------------|
| Closed, strong support | one calm disclosure row under the answer | `Show supporting evidence` |
| Open, strong support | slim merged evidence rows, then secondary pills | support rows explain why each source matters |
| Closed, thin support | same disclosure row remains present | no alarming chrome; limitation stays inside the disclosure |
| Open, thin support | compact limited-evidence message plus any surviving jumps | explicitly state that support is limited |
| Open, empty support | compact empty-evidence message | explain that this answer view does not have mapped support available |

## Phase Boundaries

- Do not redesign the narrative answer body here; that was Phase 17.
- Do not change the confidence pill or explainer contract here; that was Phase 18.
- Do not add inline charts here; that is Phase 20.
- Do not make the secondary pills conditional on disclosure state.
- Do not reintroduce a right-rail support layout or always-visible finding wall.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `collapsible` or `accordion`-style disclosure primitive, existing `button`/`badge`/`separator` patterns as needed | required |
| third-party | none | not applicable |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-04-24
