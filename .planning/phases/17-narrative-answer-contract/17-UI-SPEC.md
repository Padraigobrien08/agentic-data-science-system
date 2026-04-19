---
phase: 17
slug: narrative-answer-contract
status: draft
shadcn_initialized: true
preset: new-york
created: 2026-04-19
---

# Phase 17 — UI Design Contract

> Visual and interaction contract for replacing the summary-first chat answer with a narrative-first analyst reply.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` with Radix base, `slate` base color, and Tailwind CSS variables |
| Component library | radix |
| Icon library | lucide |
| Font | `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`; display accents `"Iowan Old Style", "Palatino Linotype", serif`; `ui-monospace` for technical metadata only |

Source: pre-populated from `frontend/components.json`, `frontend/tailwind.config.ts`, `frontend/src/app/globals.css`, and `npx shadcn info`.

---

## Visual Hierarchy

**Primary focal point:** the lead thesis and short narrative sections inside the assistant answer card.

**Reading order:**
1. lead thesis sentence
2. `What's happening`
3. `Why we think that`
4. `What weakens the claim`
5. existing secondary findings, confidence, and evidence surfaces
6. technical disclosure and secondary navigation

**Rules:**

- The first viewport of a completed answer must read like an analyst memo, not a dashboard of stacked utility cards.
- Keep the answer card inside the existing transcript cap of `64rem`, but constrain the prose column itself to roughly `46rem` or `65-72` characters on desktop.
- The narrative block spans the full card width before any secondary grid or aside begins.
- Do not place evidence pills, confidence chrome, or technical-status disclosure above the thesis.
- Reserve uppercase micro-labels for the eyebrow and technical metadata only. Narrative section headings render in title case.
- Limited-support answers keep the same shell and placement as full answers. They are not a separate empty-state card.

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Inline punctuation gaps, badge internals, hairline visual rhythm |
| sm | 8px | Heading-to-body gap, compact chip spacing, microcopy stacks |
| md | 16px | Default paragraph gap, mobile card padding, section-to-section rhythm |
| lg | 24px | Desktop card padding, narrative-to-secondary-surface separation |
| xl | 32px | Large internal section breaks inside the answer card |
| 2xl | 48px | Empty-state vertical spacing and large transcript breathing room |
| 3xl | 64px | Page-level spacing only |

Exceptions: `40px` minimum composer button height; `44px` minimum tap target for any mobile pill or button; narrative block to secondary surfaces uses `24px` minimum separation and may not collapse below that.

Source: inherits the Phase 14 scale, current chat-shell densities, and the existing 4-point Tailwind rhythm in `chat-message-list.tsx`, `chat-run-answer-card.tsx`, and `chat-composer.tsx`.

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.6 |
| Label | 10px | 600 | 1.2 |
| Heading | 14px | 600 | 1.3 |
| Display | 20px | 600 | 1.25 |

Rules:

- Use only weights `400` and `600` in this phase.
- The thesis is the only display-sized text in the answer card.
- Narrative section headings use the `Heading` role in title case. Do not reuse all-caps metadata styling for prose sections.
- Body copy stays single-column and never collapses below `14px`.

Source: body/display sizes are adjusted from the current chat answer card for narrative readability and locked to the Phase 17 requirement for a substantive `120-220` word reading surface.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `hsl(var(--ui-background))` / `#f5f7fb` | Workspace canvas, transcript background, quiet answer-card backdrop |
| Secondary (30%) | `hsl(var(--ui-card))` / `rgba(255,255,255,0.97)` | Narrative surface, secondary panels, composer shell |
| Accent (10%) | `hsl(var(--ui-primary))` / `#1f6fff` | Composer primary action, inline narrative source links, focus-visible outlines |
| Destructive | `hsl(var(--ui-destructive))` / `#dc2626` | Destructive actions only |

Accent reserved for: the composer primary action, inline narrative source links, and focus-visible outlines. Do not use accent on section headings, fallback qualifiers, evidence pills, or the thesis body.

Warning tones: use inherited amber sparingly for one-line partial-mode qualifiers or blocking caveat notes only. Never wash the whole answer card in warning styling for `partial` mode.

Source: pre-populated from `frontend/src/app/globals.css`, `frontend/tailwind.config.ts`, and the existing shadcn variable mapping.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | `Run analysis` |
| Empty state heading | `Start the first analysis` |
| Empty state body | `Describe the question or thesis you want checked against this workspace's tickers. The reply will render as a narrative answer, not a summary card.` |
| Error state | `This analysis didn't finish cleanly. Open trace to inspect the failure, then rerun with adjusted scope or wording.` |
| Destructive confirmation | `None`: Phase 17 introduces no destructive actions or confirmation flows. |

Voice rules:

- Use analyst-memo voice: direct, cautious, concrete.
- Never use `assistant`, `AI`, `great question`, `based on the available information`, or generic success phrases.
- Lead with the claim, not the process.
- `What weakens the claim` must name real uncertainty or missing support, not boilerplate disclaimers.

Source: tone and fallback constraints are pre-populated from `17-CONTEXT.md` decisions `D-05` through `D-10`; `Run analysis` is a phase default because upstream artifacts did not lock composer CTA copy.

---

## Component Contract

### Narrative answer shell

- Keep the existing assistant-card container and transcript placement from Phase 14.
- Replace the current summary-first header with a full-width narrative block before any secondary surfaces.
- Use a small eyebrow label `Answer`.
- The narrative block contains one thesis and up to three short sections in this fixed order: `What's happening`, `Why we think that`, `What weakens the claim`.
- Do not use bullets, badges, or chip stacks inside the narrative copy itself in Phase 17.
- Target total narrative length of `120-220` words for `mode="full"`.

### Thesis block

- Render the thesis as one prominent sentence, optionally two short sentences when the claim needs a bounded qualifier.
- Keep the thesis visually stronger than section copy through size and weight, not color.
- Put any quiet supporting rider under the thesis, not above it.

### Narrative sections

- Each section is one short paragraph.
- Section heading-to-body gap uses `8px`; section-to-section gap uses `16px`.
- Omit sections that have no specific content. Do not substitute filler copy.
- `What's happening` explains the observed pattern.
- `Why we think that` cites the strongest support in prose.
- `What weakens the claim` names the evidence limits or counter-signals.

### Partial-answer mode

- `mode="partial"` uses the same shell as a full narrative.
- Render one compact paragraph of `60-120` words that states the strongest supportable claim and the missing or weak evidence.
- Allow an optional one-line muted qualifier beneath it for fallback reason, but keep that qualifier quieter than the paragraph itself.
- Never show `Analysis completed for ...`, `No summary available`, or mirrored takeaway bullets as the main fallback.

### Secondary surfaces

- Existing findings, confidence, caveat, and evidence sections from Phase 15 may remain, but they must sit below the narrative block with at least `24px` separation.
- Secondary surfaces may use the existing calmer panels and pill treatments, but they cannot outrank the narrative in vertical order or contrast.
- Keep technical disclosure and navigation below the prose body.

### Pending placeholder

- Pending state should mirror the narrative structure: one thesis skeleton line and two to three body skeleton groups.
- Avoid the old `Conclusion` plus `Goal` placeholder pattern for this phase.

---

## Interaction Contract

- New runs and historical runs must render inside the same narrative card shell. Older runs without `narrative_answer` use the legacy derivation path, but they should not visibly fall back to an older card design.
- The narrative sections are always expanded. Do not add accordion, tab, or disclosure behavior inside the answer prose in Phase 17.
- Inline narrative links may jump to the existing artifact or trace surfaces only. No modal, drawer, or embedded report viewer in chat.
- Keyboard focus order should move from the narrative block to secondary evidence and navigation items, then to any technical disclosure.
- Limited-evidence answers must occupy the same position and approximate height class as successful answers so transcript replacement does not feel abrupt.
- Composer submission and history hydration remain unchanged from earlier phases.

---

## State Contract

| State | Visual Contract | Copy Contract |
|-------|-----------------|---------------|
| Pending | Full answer card shell with thesis and section skeleton rhythm | `Running analysis...` only in pending chrome; no fake narrative sentences |
| Full narrative | Full-width thesis plus `2-3` titled prose sections; narrative appears before any secondary panels | `120-220` words total; lead with the claim, then support, then watchouts |
| Partial narrative | Same shell, one compact paragraph, optional muted fallback-reason line | State the strongest supportable claim and name missing or weak evidence; never generic success copy |
| No data | Reuse partial-narrative treatment, but make the absence explicit in the prose | Explain what was checked and what supporting data did not materialize |
| Error | Keep the compact failure treatment from Phase 14 and Phase 15; do not fabricate a narrative body | `This analysis didn't finish cleanly.` plus the trace-oriented recovery path |
| Legacy historical run | Use the narrative shell with legacy-derived copy when the new backend preview is absent | Prefer existing summary and takeaway material, but do not expose raw system or process text as the thesis |

---

## Phase Boundaries

- Do not move confidence into the answer header. That belongs to Phase 18.
- Do not redesign evidence into a disclosure beneath the answer. That belongs to Phase 19.
- Do not add inline charts or chart captions. That belongs to Phase 20.
- Do not re-promote the standalone run page as the main reading surface.
- Do not add markdown rendering inside the primary chat answer.
- Do not introduce new third-party component registries for this phase.

Source: pre-populated from `17-CONTEXT.md`, `17-RESEARCH.md`, `REQUIREMENTS.md`, and the existing Phase 14-16 UI contracts.

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `badge`, `button`, `card`, `separator`, `skeleton` | not required |
| third-party | none | not applicable |

Source: pre-populated from `frontend/components.json`, `npx shadcn info`, and the installed `frontend/src/components/ui` inventory. No third-party registries are declared for this phase.

---

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
