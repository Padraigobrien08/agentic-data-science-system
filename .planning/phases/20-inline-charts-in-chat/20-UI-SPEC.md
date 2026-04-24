---
phase: 20
slug: inline-charts-in-chat
status: draft
shadcn_initialized: true
preset: new-york
created: 2026-04-24
---

# Phase 20 - UI Design Contract

> Visual and interaction contract for adding deterministic inline charts as visual proof inside the chat answer without turning the answer into a dashboard.

## Design System

| Property | Value |
|----------|-------|
| Tool | shadcn |
| Preset | `new-york` |
| Component library | radix |
| Icon library | lucide |
| Font | inherit Phase 17-19 stack: `"Avenir Next", "Segoe UI", "Helvetica Neue", sans-serif`; keep `font-display` out of chart chrome and captions |

Source: aligned to `frontend/components.json`, `npx shadcn info`, `frontend/src/app/globals.css`, the shipped Phase 19 answer shell, and Phase 20 context/research artifacts.

## Visual Hierarchy

**Primary focal point:** the narrative answer thesis and prose.

**Secondary focal point:** the confidence pill in the answer header.

**Tertiary focal points:**
1. one inline `Visual evidence` section between prose and disclosure
2. at most two chart cards stacked vertically
3. supplemental evidence disclosure and secondary navigation beneath charts

**Rules:**

- Charts are evidentiary support, not the answer itself.
- Render charts only when backend-owned preview data exists and passes deterministic trust gating.
- Keep charts inside the same centered answer column already used by `ChatRunAnswerCard`; no right rail, no breakout dashboard width.
- One chart is the default. A second chart is allowed only when it explains a distinct supporting angle such as trend plus peer comparison.
- Do not place two charts side by side in Phase 20. A two-up grid reads like analytics chrome and weakens the answer-first hierarchy.
- The chart section should feel stronger than the disclosure trigger below it, but quieter than the prose above it.

## Spacing Scale

Reuse the existing 4-point rhythm and lock chart spacing to the answer shell already shipping in Phase 19.

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | marker offsets, micro gaps inside tooltip rows, inline color chips |
| sm | 8px | caption-to-label spacing, compact key spacing, tooltip internals |
| md | 16px | chart card padding on mobile, caption spacing, stack gap for small supporting elements |
| lg | 24px | chart-to-chart gap, narrative-to-chart transition, disclosure separation |
| xl | 32px | desktop section breathing room inside the answer card |
| 2xl | 48px | transcript-level separation only; not for chart-card internals |
| 3xl | 64px | page-level spacing only; never inside the answer column |

Exceptions: chart plot area uses explicit height, not content-driven height. Set `min-height: 220px` on mobile and `min-height: 240px` on desktop; cap visual height around `280px`.

Rules:
- The first chart should sit after the narrative block with `lg` separation, not pressed against the thesis copy.
- Two charts stack with `lg` vertical rhythm and shared width.
- Captions belong below the plot with `sm` to `md` separation. Do not overlay captions inside the plotted area.
- Keep chart-card padding calmer than a marketing card: `md` on mobile, `lg` on desktop.

## Typography

Declare four sizes only for this phase and keep weights to `400` and `600`.

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 16px | 400 | 1.65 |
| Label | 10px | 600 | 1.2 |
| Caption / Utility | 13px | 400 | 1.5 |
| Display | 20px | 600 | 1.5 |

Rules:
- The thesis keeps the existing display role; charts must not introduce a louder headline.
- `Visual evidence` overlines, axis labels, and any compact series key reuse the `Label` role.
- Captions, tooltip rows, and limited-visual-evidence notices use `Caption / Utility`.
- Do not introduce a third weight for chart chrome. Quietness should come from color and spacing, not more font variants.

## Color

Reuse the existing light workspace palette and add stable chart tokens that map to the current blue/warm/gold language instead of a generic rainbow.

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#f5f7fb` / `hsl(var(--ui-background))` | transcript background, page field, answer surroundings |
| Secondary (30%) | `#ffffff` / `hsl(var(--ui-card))` plus existing surface tokens | answer card, chart card, tooltip surface, disclosure container |
| Accent (10%) | `#1f6fff` primary with chart tokens `--chart-1: #1f6fff`, `--chart-2: #ff8a5b`, `--chart-3: #f2c56d`, `--chart-4: #5f6b82` | focal series, comparison series, explicit markers, exact source links, focus rings |
| Destructive | `hsl(var(--ui-destructive))` | chart-preview failure state only |

Accent reserved for: focal trend line, focal grouped bars, peer median comparison bars, deterministic event markers, chart focus ring, and exact `Open source` links. Never use accent to tint the entire chart card, caption block, or answer background.

Rules:
- Add chart tokens to `frontend/src/app/globals.css` before rendering charts.
- Use stable series colors across every answer: focal metric always maps to `--chart-1`; peer median or comparison series always maps to `--chart-2`.
- Grid lines, axes, and non-data scaffolding stay neutral and low contrast.
- Confidence semantics remain owned by the existing confidence pill; charts do not inherit green/amber/red answer-state coloring.

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | `Show supporting evidence` |
| Empty state heading | `No chart shown` |
| Empty state body | `This answer does not include a chart because the run did not produce strong, deterministic visual evidence. Read the answer and open supporting evidence for the source material.` |
| Error state | `Chart preview unavailable. Read the answer text, then open supporting evidence or trace to inspect the underlying run artifacts.` |
| Destructive confirmation | `none`: `No destructive chart action exists in this phase.` |

Additional phase copy:

- Section overline above the chart stack: `Visual evidence`
- Caption style: one short sentence explaining what the chart shows and why it matters
- Source jump label remains inherited: `Open source`

Rules:
- Captions must sound like analyst support notes, not dashboard labels.
- Do not use chart titles like `Revenue Trend Widget` or `Peer Comparison View`.
- Tooltips should expose metric and period labels only; they are not prose surfaces.
- If no eligible chart exists, omit the chart section entirely in normal success states. Use the empty-state copy only when the UI intentionally reserves the visual-evidence slot after a preview failure or explicit limited-visual-evidence response.

## Component Contract

### Chart section boundary

- Insert the chart section inside `ChatRunAnswerCard` after the bordered narrative block and before the supplemental evidence disclosure.
- Render the section only when `inlineCharts.length > 0` or when a chart-preview failure message is explicitly surfaced.
- Show one quiet `Visual evidence` label once above the chart stack. Do not repeat the label on every chart card.

### Chart stack

- Layout is always one column in Phase 20.
- Maximum count is `2`.
- Preferred ordering:
  1. trend line chart
  2. peer comparison grouped bar chart
- If only one chart passes gating, render one chart with no empty second slot.

### Chart card

- Container should match the existing answer language: rounded `1.15rem` to `1.5rem`, thin border, white or near-white surface, no heavy dashboard shadow.
- Internal order:
  1. optional compact series key when more than one visible series exists
  2. plot area
  3. short caption
- Plot area rules:
  - explicit min height required
  - horizontal grid lines only
  - no dense axis chrome
  - no background fills behind the plotted data
- Keep the card visually lighter than the disclosure panel below it.

### Line trend chart

- Use for deterministic trends only.
- Stroke width: `2px`.
- Hide point dots by default.
- Show marker dots or reference markers only when the backend preview explicitly includes deterministic event markers.
- Do not use area fills, spline dramatization, or gradient fills in Phase 20.

### Grouped bar peer chart

- Use only for trusted peer comparisons.
- Default visible series count is `2`: focal company and peer median.
- Rounded bar corners are acceptable, but keep radius subtle.
- If the backend preview exposes more than three direct series, collapse comparison to peer median rather than drawing a crowded legend.

### Caption contract

- Exactly one caption per chart.
- Caption length target: `90-160` characters.
- Structure:
  - first clause = what the visual shows
  - second clause = why it matters to the answer
- Captions sit below the plot, left-aligned, in muted body color.

### Tooltip contract

- Interaction stays hover-only.
- Tooltip content order:
  1. period or category label
  2. each visible series name and formatted value
- Tooltip surface uses the same neutral card language as other answer chrome.
- No click-to-pin, no sticky tooltip, no drill-in, no cross-filtering.

## Interaction Contract

- The answer must remain legible without hovering any chart point or bar.
- Hover reveals formatted detail; leaving the plot dismisses the tooltip immediately.
- Keyboard focus and screen-reader support must rely on Recharts accessibility support through the shadcn chart wrapper.
- Chart hover should not interfere with scrolling the chat transcript.
- Clicking a chart should do nothing in Phase 20. Source inspection continues through the existing disclosure rows and navigation pills.

## State Contract

| State | Visual Contract | Copy Contract |
|------|-----------------|---------------|
| One eligible chart | one chart card between prose and disclosure | one caption explaining what it shows and why it matters |
| Two eligible charts | two stacked cards, same width, same chrome | each caption explains a distinct evidence angle |
| No eligible chart | omit the chart section entirely; answer flows straight to disclosure | no placeholder copy in normal success cases |
| Chart preview unavailable | replace the chart card with one slim fallback notice in the chart slot | `Chart preview unavailable. Read the answer text, then open supporting evidence or trace to inspect the underlying run artifacts.` |
| Pending run | no chart placeholder beyond the existing pending answer shell | no chart-specific pending copy |

## Phase Boundaries

- Do not add pie, donut, radar, heatmap, or decorative area-chart families.
- Do not add chart filters, metric switches, compare controls, tabs, pinning, or persistence.
- Do not infer chart types or series from narrative prose or raw frontend payloads.
- Do not parse CSV artifacts in the browser.
- Do not make charts the primary escape hatch into trace or artifacts. Existing evidence rows and pills keep that role.
- Do not introduce a chart legend bar, toolbar, or side panel that turns the answer into a mini dashboard.

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `chart` plus existing local `card`, `collapsible`, and `popover` patterns as needed | official-only registry, no additional vetting required - 2026-04-24 |
| third-party | none | not applicable - 2026-04-24 |

## Checker Sign-Off

- [ ] Dimension 1 Copywriting: PASS
- [ ] Dimension 2 Visuals: PASS
- [ ] Dimension 3 Color: PASS
- [ ] Dimension 4 Typography: PASS
- [ ] Dimension 5 Spacing: PASS
- [ ] Dimension 6 Registry Safety: PASS

**Approval:** pending
