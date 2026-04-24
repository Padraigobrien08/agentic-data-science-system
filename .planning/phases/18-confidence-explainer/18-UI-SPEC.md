---
phase: 18
slug: confidence-explainer
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-24
reviewed_at: 2026-04-24T20:55:00Z
---

# Phase 18 — UI Design Contract

> Visual and interaction contract for moving evidence strength into the answer header and explaining it through a compact, integrated disclosure.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` |
| Component library | radix |
| Icon library | lucide |
| Font | inherit Phase 17 stack: `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`; no new display font changes in this phase |

Source: aligned to the initialized `frontend/components.json`, existing Phase 17 narrative answer surface, and current chat answer shell.

## Visual Hierarchy

**Primary focal point:** the narrative answer thesis and prose.

**Secondary focal point:** the inline evidence-strength pill in the answer header.

**Tertiary focal points:**
1. short inline rider when needed
2. supporting detail beneath the answer
3. explainer content only after the user asks for it

**Rules:**

- Confidence must feel integrated with the answer, not bolted on below it.
- The answer header remains calm: one label on the left, one confidence pill on the right.
- The confidence pill is informative, not promotional. It should not outshine the thesis.
- The explainer must feel like a small contextual layer, not a new page or a second content column.
- The old lower-page `confidence + caveats` block should no longer dominate the primary reading path.

## Spacing Scale

Reuse the Phase 17 spacing system and bias toward compact header density:

| Token | Value | Usage |
|------|------|--------|
| xs | 4px | chevron gap, inline separators, compact badge internals |
| sm | 8px | pill internal spacing, microcopy spacing |
| md | 16px | answer-header row gap, popover section spacing |
| lg | 24px | separation between narrative answer and lower support content |
| xl | 32px | only for card-level breathing room on desktop |

Rules:
- The header row should feel tighter than the body prose.
- The confidence pill should fit naturally on the same line as the answer heading on desktop.
- The explainer interior uses `sm` to `md` rhythm; it must not feel like a full modal with giant spacing.
- On narrow screens, the pill may wrap below the heading, but it must still feel attached to the header block.

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.7 |
| Label | 10px | 600 | 1.2 |
| Heading | 18px | 600 | 1.35 |
| Confidence pill text | 12px | 600 | 1.2 |
| Explainer body | 13px | 400 | 1.5 |

Rules:
- `Answer` remains the quiet section label.
- The confidence pill text is smaller than the thesis and equal or slightly stronger than other utility controls.
- Explainer headings should read as quiet labels, not as mini-card titles.
- Avoid monospace in the explainer except for truly technical secondary surfaces, which are out of scope here.

## Color

Reuse the existing workspace neutrals and add semantic confidence treatment only where needed.

| Role | Value | Usage |
|------|-------|-------|
| Dominant | existing canvas / card neutrals | transcript, answer card, explainer body |
| Good | muted green tint + green text/border | `Good` evidence strength |
| Medium | muted amber tint + amber text/border | `Medium` evidence strength |
| Bad | muted red tint + red text/border | `Bad` evidence strength |
| Not rated | neutral gray tint + muted text/border | `Not rated` evidence strength |

Rules:
- Color belongs primarily to the confidence pill and only lightly to the explainer emphasis.
- Do not color the whole answer card based on confidence.
- `Medium` must be amber/yellow, not orange-red.
- `Good` and `Bad` should be legible in both light and dark surfaces without becoming saturated badges.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Header label | `Answer` |
| Confidence pill prefix | `Evidence strength:` |
| Confidence labels | `Good`, `Medium`, `Bad`, `Not rated` |
| Explainer sections | `What supports this rating`, `What weakens it`, `What limits the evidence` |
| Inline rider | one short sentence only, used when immediate caution is warranted |

Rules:
- Do not expose backend labels like `high`, `low`, or raw `critic/report` statuses in the primary answer.
- Do not use assistant-like phrases such as `Here’s why`.
- The explainer copy should sound like an analyst explaining support quality, not like QA or monitoring copy.
- The inline rider should be cautionary and concrete, not repetitive of the explainer.

## Component Contract

### Answer header

The answer header contains exactly two primary elements:

1. left: quiet `Answer` label
2. right: a compact clickable confidence pill with integrated chevron

On mobile, the confidence pill may wrap beneath the label, but it must remain in the same header block.

### Confidence pill

- Shape: compact rounded pill
- Contents: `Evidence strength: {Label}` plus chevron
- States:
  - `Good` → green treatment
  - `Medium` → amber treatment
  - `Bad` → red treatment
  - `Not rated` → neutral treatment
- The pill is the only visible confidence control in the primary answer header.

### Explainer disclosure

- Preferred desktop behavior: compact shadcn popover anchored to the pill
- Acceptable narrow-screen fallback: dialog or sheet if popover space becomes awkward
- Content structure:
  1. compact heading row with current evidence-strength label
  2. grouped rationale blocks:
     - `What supports this rating`
     - `What weakens it`
     - `What limits the evidence`
- Each group is a short list or concise stack, not long prose
- The explainer must stay comfortably scannable without scrolling in normal desktop cases

### Inline rider

- Render directly below the narrative answer only when the backend/view model says immediate caution is needed
- Maximum density: one short sentence
- No badge cluster, no stacked caveat list, no repeated confidence strip

### Transitional compatibility

- Secondary surfaces may continue to use older confidence components temporarily if needed
- The primary chat answer should move first to the new header-prompted explainer model
- Do not make the answer card show both the old `ConfidenceStrip` and the new pill

## Interaction Contract

- The user should understand evidence posture at a glance before opening the explainer.
- Clicking or pressing the confidence pill opens the explainer in place; it should not navigate away.
- Keyboard interaction and focus return must be clean and predictable.
- Closing the explainer returns the user to the pill trigger.
- The explainer is supplemental: it clarifies the answer, but the answer must still read coherently without opening it.

## State Contract

| State | Visual Contract | Copy Contract |
|------|-----------------|---------------|
| Good | green semantic pill, no visual alarm | answer reads confidently but still cautiously |
| Medium | amber semantic pill, optional short rider if needed | answer acknowledges support with meaningful caveats |
| Bad | red semantic pill, likely short rider visible | answer clearly signals weak support or serious trust limits |
| Not rated | neutral pill | answer can still render, but should not imply strong backing |
| Error / no confidence data | no special fallback modal; use neutral or hidden state per derived view model | confidence should not invent justification |

## Phase Boundaries

- Do not redesign the supplemental evidence section here.
- Do not add charts here.
- Do not turn the explainer into a large permanent side panel or full-page card.
- Do not surface raw `critic: success` / `report: success` labels in the primary answer.
- Do not rework trace or run inspection surfaces in this phase.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `badge` plus one disclosure primitive (`popover`, `dialog`, or `sheet`) | required |
| third-party | none | not applicable |

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-04-24
