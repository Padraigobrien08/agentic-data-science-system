---
phase: 08
slug: summary-first-large-trace-views
status: approved
shadcn_initialized: true
preset: new-york
created: 2026-04-18
reviewed_at: 2026-04-18T14:10:26Z
---

# Phase 08 — UI Design Contract

> Visual and interaction contract for summary-first large trace views. Generated after Phase 08 context and research, with shadcn initialized in `frontend/`.

---

## Design System

| Property | Value |
|----------|-------|
| Tool | `shadcn/ui` |
| Preset | `new-york` |
| Component library | `Radix UI primitives via shadcn/ui` |
| Icon library | `lucide-react` |
| Font | `Avenir Next`, `Segoe UI`, `Helvetica Neue`, sans-serif; `ui-monospace` for trace metadata |

---

## Visual Hierarchy

**Primary focal point:** the run overview and step timeline preview. The first screen must answer "what happened in this run?" before it exposes any deep audit payloads.

**Reading order:**
1. Status + run overview summary
2. Step timeline preview
3. Collection summary row: `Steps`, `Artifacts`, `Model calls`
4. Active collection list with search/filter/pagination
5. Per-item detail pane or drawer

**Layout rules:**
- No floating collage cards or decorative widget stacks.
- The overview and timeline should read as one continuous analysis surface, not a dashboard mosaic.
- Collection summaries may sit in a 3-column desktop row, but the active collection list beneath them must use a single primary content column.
- Raw payload inspection is always subordinate to the summary view and never visible by default.

**Icon-only controls:**
- Avoid icon-only actions in the primary trace workflow.
- If an icon-only affordance is unavoidable, it must include an `aria-label`, tooltip, and text equivalent in an overflow or mobile-safe action row.

---

## Component Inventory

| Surface | Components |
|---------|------------|
| Trace shell | `Card`, `Separator`, `Badge`, existing technical `Section` wrappers until migrated |
| Collection summary row | `Card`, `Button`, `Badge` |
| Query controls | `Input`, `Select`, `Tabs`, `Button` |
| Collection results | `Table` for desktop, stacked cards for narrow screens |
| Raw detail expansion | `Sheet` on desktop, inline expandable panel on narrow screens |
| Loading and empty states | `Skeleton`, `Badge`, muted helper copy |

**Installed now:** `Button`  
**Planned for this phase:** `Card`, `Input`, `Select`, `Tabs`, `Sheet`, `Table`, `Badge`, `Separator`, `Skeleton`

---

## Spacing Scale

Declared values (must be multiples of 4):

| Token | Value | Usage |
|-------|-------|-------|
| xs | 4px | Hairline inline gaps, badge icon spacing |
| sm | 8px | Chip spacing, compact metadata rows |
| md | 16px | Default control gaps and card padding start |
| lg | 24px | Section padding and collection-group spacing |
| xl | 32px | Major panel gaps on desktop |
| 2xl | 48px | Page section breaks |
| 3xl | 64px | Top-level page breathing room |

Exceptions: none

---

## Typography

| Role | Size | Weight | Line Height |
|------|------|--------|-------------|
| Body | 14px | 400 | 1.5 |
| Label | 12px | 600 | 1.4 |
| Heading | 18px | 600 | 1.3 |
| Display | 30px | 600 | 1.1 |

**Rules:**
- Use only `400` and `600` weights in this phase.
- Monospace remains reserved for IDs, timestamps, status codes, and machine-derived trace facts.
- The trace page is an operator workflow: use typographic restraint, not marketing-style type contrast.

---

## Color

| Role | Value | Usage |
|------|-------|-------|
| Dominant (60%) | `#F5F7FB` | Page canvas, full-width trace background |
| Secondary (30%) | `rgba(255, 255, 255, 0.88)` | Summary cards, collection panes, sticky rails |
| Accent (10%) | `#1F6FFF` | Active collection tab, primary inspect action, current pagination item, focus ring, selected evidence link |
| Destructive | `#DC2626` | Error banners and future destructive admin/debug actions only |

Accent reserved for: active collection state, one primary inspect action per surface, keyboard focus styling, and selected evidence or timeline link state. It must not be used for all buttons, all links, or all badges.

**Split:** 60/30/10 is explicit for this phase. Warm landing-page accents are out of scope here.

---

## Interaction Contract

### Default opening state
- First render shows a compact run overview, a bounded timeline preview, and collection summaries.
- First render does **not** show raw `output_payload_json`, raw `meta_json`, full step payloads, or model-call request/response blobs.
- The technical inspector remains available, but it opens below the summary-first experience and stays collapsed by default.

### Collection navigation
- `Steps`, `Artifacts`, and `Model calls` remain separate navigable collections.
- The active collection is controlled by URL state so search/filter/pagination are shareable and SSR-friendly.
- Collection filters must stay compact and single-line on desktop where possible; avoid bulky filter sidebars.
- Pagination or cursor controls must appear at both the top and bottom when a collection spans more than one page.

### Timeline spine
- The timeline is the canonical spine.
- Artifact and model-call rows must expose at least one visible link-back cue to the timeline:
  - step index
  - phase/lane badge
  - linked evidence/status chip

### Raw detail expansion
- Raw payload fetches are per-item and privileged.
- Desktop default: open raw detail in a right-side `Sheet`.
- Narrow screens: use inline expansion beneath the selected row.
- Only one raw-detail surface should be open at a time.

### Mobile behavior
- Summary cards stack vertically.
- Timeline preview stays above collection results.
- Filter controls collapse into a concise row; never force a full-screen filter experience for the default path.

---

## Copywriting Contract

| Element | Copy |
|---------|------|
| Primary CTA | `Inspect step details` |
| Empty state heading | `No trace details yet` |
| Empty state body | `This run has not produced trace records yet. Wait for execution to finish, reopen the run answer, or retry the run if it is stuck.` |
| Error state | `Trace details couldn't load. Reload this page. If the issue persists, open the run answer or return to the runs list while the backend finishes processing.` |
| Destructive confirmation | `None in Phase 08` |

**Additional labels to standardize:**
- collection action: `View all steps`
- admin raw action: `Open raw payload`
- artifact action: `Open artifact preview`
- model call action: `Inspect model call`

Do not use generic labels such as `Open`, `View`, `Submit`, or `Details` on their own.

---

## Collection-Specific UX

### Steps
- Default sort: ascending `step_index`
- Required row fields: step index, lane/phase cue, status, tool/label, time range
- Secondary row action: `Inspect step details`

### Artifacts
- Default sort: by linked timeline order first, then creation time
- Required row fields: role, kind, size, linked step or phase cue
- Primary row action: `Open artifact preview`

### Model calls
- Default sort: chronological
- Required row fields: model name, prompt version, status, latency, token total
- Primary row action: `Inspect model call`

---

## Registry Safety

| Registry | Blocks Used | Safety Gate |
|----------|-------------|-------------|
| shadcn official | `button` installed; `card`, `input`, `select`, `tabs`, `sheet`, `table`, `badge`, `separator`, `skeleton` planned | not required |
| third-party | none | not applicable |

---

## Checker Sign-Off

- [x] Dimension 1 Copywriting: PASS
- [x] Dimension 2 Visuals: PASS
- [x] Dimension 3 Color: PASS
- [x] Dimension 4 Typography: PASS
- [x] Dimension 5 Spacing: PASS
- [x] Dimension 6 Registry Safety: PASS

**Approval:** approved 2026-04-18
