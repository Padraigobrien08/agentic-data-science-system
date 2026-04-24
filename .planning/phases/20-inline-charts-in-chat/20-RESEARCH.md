# Phase 20: Inline Charts in Chat - Research

**Researched:** 2026-04-24
**Domain:** Deterministic inline chart previews for narrative chat answers
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Charts should render only when they materially strengthen the answer.
- **D-02:** Responses should be capped at `1-2` charts.
- **D-03:** Phase 20 should treat charts as evidentiary support, not decorative content or a default answer embellishment.
- **D-04:** Backend should emit explicit safe chart specs derived from trusted artifacts or metric outputs.
- **D-05:** Frontend should only render those specs and should not infer chart types from raw answer content.
- **D-06:** Chart rendering must preserve the deterministic trust model already established for narrative previews, confidence, and supplemental evidence.
- **D-07:** Charts should render inline beneath the prose answer and confidence header.
- **D-08:** Charts should appear above the supplemental evidence disclosure.
- **D-09:** Phase 20 should preserve the answer-first reading order: narrative answer, visual proof, deeper evidence.
- **D-10:** The initial chart set should include line charts for trends.
- **D-11:** The initial chart set should include grouped bar charts for peer comparisons.
- **D-12:** Simple marker or timeline overlays are allowed only when the underlying data is already explicit and deterministic.
- **D-13:** Phase 20 should not expand into pie, donut, or other decorative chart families.
- **D-14:** Every chart should include one short caption explaining what it shows and why it matters.
- **D-15:** Interaction should stay lightweight: hover tooltips only.
- **D-16:** Phase 20 should not introduce chart filters, metric switches, or broader BI-style controls.

### Claude's Discretion
- Exact heuristic for whether a chart “materially strengthens” a given answer, as long as it stays within the 1-2 chart cap
- Exact chart card styling and responsive treatment within the centered answer column
- Exact tooltip and caption copy style

### Deferred Ideas (OUT OF SCOPE)
- User-controlled chart filters, metric switches, or chart-builder behavior
- More decorative or non-core chart families beyond line, grouped bar, and narrow explicit overlays
- Persisting or pinning charts across follow-up messages
- Broader responsive and presentation polish beyond what is needed to fit charts into the current answer shell — Phase 21
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| CHRT-01 | User can see deterministic inline charts in chat when trusted run data supports a visual explanation | Backend chart-preview builder, deterministic gating rules, and inline answer-card placement between narrative and disclosure |
| CHRT-02 | Charts are rendered from explicit backend-safe chart specs derived from trusted run artifacts or metrics, not ad hoc frontend inference | Typed `RunTransparencySummary.inline_charts` contract, persisted traceability source, frontend render-only mapping |
| CHRT-03 | Each inline chart includes a short caption explaining what it shows and why it is relevant to the answer | Backend-authored deterministic caption field on every chart preview |
</phase_requirements>

## Summary

Phase 20 should extend the same pattern established in Phases 17-19 rather than opening a new answer path. The safe boundary stays in the backend: build a bounded `inline_charts` preview from existing deterministic artifacts, persist that preview under `meta_json.ai_agents.traceability.report`, project it through `RunTransparencySummary`, and let `frontend/src/lib/run-primary-view.ts` map it into a chat view model. The frontend should not inspect raw CSV artifacts, infer chart families from prose, or accept arbitrary Recharts props from the backend.

The repo already has the right seams for this. `backend/agents/traceability_summary.py` is the existing place where safe narrative and confidence previews are built; `backend/schemas/run_transparency.py` is the typed API projection; `frontend/src/lib/run-primary-view.ts` is the single derivation seam used by both live chat replies and hydrated history; and `frontend/src/components/chat-shell/chat-run-answer-card.tsx` already has the exact insertion point required by the Phase 20 context: below prose and confidence, above supplemental evidence.

Use `features_csv` as the numeric source for plotted values, and use `trend_break_signals_csv` plus `peer_signals_csv` as deterministic selection and gating metadata. That keeps chart previews grounded in existing pipeline outputs, avoids new analytical logic, and lets the planner split the phase cleanly into backend contract work, frontend render work, and gating/test work.

**Primary recommendation:** Persist at most two backend-authored chart previews per run, render them with shadcn `chart` + Recharts inside the existing answer card, and gate them strictly by artifact-backed trend/peer rules rather than narrative text inference.

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `recharts` | `3.8.1` (published 2026-03-25) | Render line and grouped-bar charts in React | Official engine behind shadcn chart, current docs verified, React 19 peer support verified from npm |
| `shadcn` chart scaffold | `4.4.0` CLI (published 2026-04-21) | Generate local `frontend/src/components/ui/chart.tsx` wrapper and theme-aware tooltip/legend primitives | Repo already uses shadcn (`frontend/components.json` exists), and official chart docs now target Recharts v3 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Existing Tailwind/CSS variables | local repo config | Provide stable chart color tokens and spacing inside the current narrative shell | Always; add `--chart-1..4` tokens in `frontend/src/app/globals.css` before rendering charts |
| Existing `run-primary-view.ts` view-model seam | local repo code | Convert snake_case wire previews into chart render props | Always; do not map raw API JSON directly in JSX |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| shadcn `chart` + Recharts | Raw Recharts only | Works, but duplicates tooltip/legend/responsive glue and drifts from the repo’s existing shadcn ownership model |
| Persisted safe chart previews | On-demand chart synthesis in `GET /v1/runs/{id}` | Avoids persistence work, but adds runtime I/O, makes history hydration less stable, and breaks the existing traceability-preview pattern |
| Backend chart selection from artifact signals | Frontend chart inference from narrative text or raw output payloads | Violates locked decisions `D-04` and `D-05` and weakens the trust boundary |

**Installation:**
```bash
cd frontend
npm install recharts@^3.8.1
npx shadcn@latest add chart
```

After scaffolding, add chart color tokens to `frontend/src/app/globals.css`. The repo already has `frontend/components.json`, so the CLI should run from `frontend/`, not repo root.

**Version verification:** Verified on 2026-04-24 with:
```bash
cd frontend
npm view recharts version time peerDependencies --json
npm view shadcn version time --json
```

Notes from verification:
- `recharts` current version is `3.8.1`; npm reports React/React DOM peer support through `^19.0.0`.
- `shadcn` current CLI version is `4.4.0`.
- Recharts ships its own TypeScript types; the official TypeScript guide says no extra `@types/recharts` package is needed.

## Architecture Patterns

### Recommended Project Structure
```text
backend/agents/
├── inline_chart_preview.py          # New deterministic chart candidate + preview builder
├── traceability_summary.py          # Persist safe chart previews into traceability.report
└── ...

backend/schemas/
└── run_transparency.py              # Parse/project inline_charts into API shape

frontend/src/components/
├── structured-answer/
│   └── inline-evidence-charts.tsx   # Answer-specific chart card renderer
└── ui/
    └── chart.tsx                    # shadcn-generated chart wrapper

frontend/src/lib/
└── run-primary-view.ts              # Map wire previews -> InlineChartView[]
```

### Pattern 1: Persisted Backend-Owned Chart Preview
**What:** Build chart previews from deterministic artifacts during run finalization, store them under `meta_json.ai_agents.traceability.report.inline_charts`, and expose them via `RunTransparencySummary.inline_charts`.

**When to use:** Always. This matches the current narrative/confidence preview pattern and keeps chat history hydration stable.

**Example:**
```python
# Source: repo pattern in backend/agents/traceability_summary.py and backend/schemas/run_transparency.py
class InlineChartPreview(BaseModel):
    kind: Literal["line", "grouped_bar"]
    chart_id: str
    caption: str
    x_axis_label: str
    y_axis_label: str
    value_format: Literal["currency", "percent", "ratio", "count", "number"]
    series: list["InlineChartSeriesPreview"]
    rows: list["InlineChartRowPreview"]
    markers: list["InlineChartMarkerPreview"] = Field(default_factory=list)
    source_artifact_roles: list[str] = Field(default_factory=list)
```

Do not send arbitrary Recharts config from the backend. Send a bounded semantic preview that the frontend can render into one of the allowed chart families.

### Pattern 2: Artifact Signals Choose Charts, Artifact Values Feed Charts
**What:** Use one artifact set to decide whether a chart is justified, and another artifact set to provide plotted values.

**When to use:** For every chart candidate.

**Recommended source split:**
- Line chart:
  - Selection/gating: `trend_break_signals_csv`
  - Values: `features_csv`
  - Optional markers: strong or moderate shift rows from `trend_break_signals_csv`
- Grouped bar chart:
  - Selection/gating: `peer_signals_csv`
  - Values: `features_csv`
  - Series: focal ticker vs peer median across recent common periods

This is the cleanest brownfield fit because `features_csv` already contains the engineered metrics used by both `peer_signals.py` and `trend_breaks.py`.

### Pattern 3: Single Derivation Seam, Render-Only Frontend
**What:** Extend `frontend/src/lib/run-primary-view.ts` to produce `inlineCharts: InlineChartView[]` with a default of `[]`, then keep JSX renderers dumb.

**When to use:** Always. Both `frontend/src/actions/runs.ts` and `frontend/src/lib/chat-run-history.ts` already depend on this seam.

**Example:**
```typescript
// Source: repo pattern in frontend/src/lib/run-primary-view.ts
export type PrimaryAnswerView = {
  // existing fields...
  inlineCharts: InlineChartView[];
};

const inlineCharts = mapInlineCharts(transparency?.inline_charts ?? []);
```

### Pattern 4: Answer-First Placement
**What:** Render charts inside `ChatRunAnswerCard` after the narrative/support note block and before the supplemental evidence disclosure.

**When to use:** Only on the chat answer path for Phase 20.

**Why:** This exactly matches locked decisions `D-07`, `D-08`, and `D-09`, and preserves the stable Phase 17-19 reading order.

### Anti-Patterns to Avoid
- **Frontend chart inference:** Do not inspect `summaryLine`, `narrativeAnswer`, or `output_payload_json` and guess which chart to build.
- **Browser CSV parsing:** Do not fetch or parse `panel.csv`, `features.csv`, or other artifacts in the browser.
- **General chart DSL:** Do not expose raw Recharts prop trees or arbitrary JSON visualization specs from the backend.
- **Dashboard creep:** Do not add tabs, filters, metric pickers, or persisted chart state in this phase.
- **Side-rail placement:** Do not reopen a right rail or hide charts inside the supplemental disclosure.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| React chart rendering | Custom SVG/Canvas chart primitives | `recharts` + shadcn `chart` component | Recharts already handles responsive layout, axes, tooltip interaction, accessibility hooks, and React integration |
| Tooltip and legend chrome | Custom hover overlay logic | `ChartTooltip`, `ChartTooltipContent`, `ChartLegend`, `ChartLegendContent` | Official shadcn pattern already themes these correctly and keeps them consistent with the repo’s UI stack |
| Responsive sizing | Ad hoc resize listeners | `ChartContainer`/`ResponsiveContainer` with explicit `min-h-*` | Recharts uses `ResizeObserver`; missing height is the actual failure mode to guard against |
| Chart selection logic | Text-matching the narrative answer | Deterministic builder from `trend_break_signals_csv`, `peer_signals_csv`, and `features_csv` | Keeps the trust boundary aligned with Phase 20 decisions |
| Period ordering | Frontend lexical sort of fiscal labels | Backend sort before preview generation | `2026-Q10`-style or mixed period strings become a future trap; backend already has period-sorting helpers |

**Key insight:** The hard part in this phase is not drawing bars or lines. It is preserving the answer trust model. That means bounded preview specs, deterministic chart selection, and zero browser-side data inference.

## Common Pitfalls

### Pitfall 1: Collapsed or Zero-Height Charts
**What goes wrong:** The chart renders as blank space or a 0-height SVG.
**Why it happens:** shadcn `ChartContainer` and Recharts responsive sizing need an explicit height, min-height, or aspect ratio.
**How to avoid:** Put a fixed `min-h-*` or `aspect-*` on the chart container/card. Keep that on the answer-specific renderer, not just a parent wrapper.
**Warning signs:** Chart DOM exists, but no visible plot area; local tests pass structurally but manual UI looks empty.

### Pitfall 2: Trust Boundary Drift
**What goes wrong:** The frontend starts deciding which chart to show by looking at prose or raw payloads.
**Why it happens:** `run-primary-view.ts` is convenient, and the browser already has the answer text.
**How to avoid:** Keep chart gating and selection in a backend helper adjacent to `traceability_summary.py`; frontend only maps and renders `inline_charts`.
**Warning signs:** Chart type depends on string matching, chart data is reconstructed from `summaryLine`, or chart JSX branches on narrative headings.

### Pitfall 3: Peer Charts on Weak Cross-Section Coverage
**What goes wrong:** A peer-comparison chart looks authoritative even when the peer set is too thin.
**Why it happens:** `peer_signals_csv` can include `rank_only` or `insufficient_peers`, and it is easy to ignore those fields.
**How to avoid:** For grouped-bar peer charts, require `peer_coverage == "full"` for the selected metric and periods. If coverage is weaker, suppress the chart instead of drawing a misleading comparison.
**Warning signs:** Captions claim peer strength while `critic_blocking_caveats` or `metric_caveats_panel_csv` still warn about limited peer coverage.

### Pitfall 4: Recharts v2 Assumptions in v3 Code
**What goes wrong:** Old interaction props or color-token patterns are copied into new code.
**Why it happens:** Many existing blog posts and examples still target Recharts 2.x.
**How to avoid:** Follow current official guidance: use Tooltip-driven interaction, use `var(--chart-n)` tokens, and keep `ChartContainer` measurable on first render.
**Warning signs:** Usage of `activeIndex`, `hsl(var(--chart-1))`, or missing container height.

### Pitfall 5: Broad Fixture Churn from a New Required View Field
**What goes wrong:** Many frontend tests fail because `ChatAnswerCardView` and `PrimaryAnswerView` literals are missing chart fields.
**Why it happens:** This repo uses explicit typed object fixtures in tests.
**How to avoid:** Make wire preview fields optional at the API layer, but default `inlineCharts` to `[]` in `run-primary-view.ts` so render paths stay simple.
**Warning signs:** Failing tests in `chat-message-list`, `chat-shell`, `chat-run-history`, `actions/runs`, and `run-inspection-panel` before any real chart assertions are added.

## Code Examples

Verified patterns from official sources and current repo seams:

### shadcn/Recharts Render Pattern
```typescript
// Source: https://ui.shadcn.com/docs/components/radix/chart
"use client";

import { Line, LineChart, CartesianGrid, XAxis } from "recharts";
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "@/components/ui/chart";

const chartConfig = {
  focal: { label: "MSFT", color: "var(--chart-1)" },
} satisfies ChartConfig;

export function InlineTrendChart({ data }: { data: Array<{ period: string; focal: number }> }) {
  return (
    <ChartContainer config={chartConfig} className="min-h-[220px] w-full">
      <LineChart accessibilityLayer data={data}>
        <CartesianGrid vertical={false} />
        <XAxis dataKey="period" tickLine={false} axisLine={false} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Line type="monotone" dataKey="focal" stroke="var(--color-focal)" strokeWidth={2} dot={false} />
      </LineChart>
    </ChartContainer>
  );
}
```

### Deterministic Backend Gating
```python
# Source: repo artifact contracts in src/features.py, src/peer_signals.py, src/trend_breaks.py
def build_inline_charts(artifact_paths: dict[str, str], *, goal_code: str | None) -> list[InlineChartPreview]:
    charts: list[InlineChartPreview] = []

    if goal_code in {"trend_deterioration", "mixed_trend_and_anomaly", "full_pipeline"}:
        line_chart = build_trend_line_preview(features_csv=artifact_paths["features_csv"],
                                              trend_breaks_csv=artifact_paths["trend_break_signals_csv"])
        if line_chart is not None:
            charts.append(line_chart)

    if goal_code == "peer_comparison" or len(charts) < 2:
        peer_chart = build_peer_bar_preview(features_csv=artifact_paths["features_csv"],
                                            peer_signals_csv=artifact_paths["peer_signals_csv"])
        if peer_chart is not None:
            charts.append(peer_chart)

    return charts[:2]
```

### Answer-Card Placement
```tsx
// Source: repo seam in frontend/src/components/chat-shell/chat-run-answer-card.tsx
<section className="space-y-6 border-b border-[var(--border)]/80 pb-8">
  {/* confidence + narrative */}
</section>

{answerCard.inlineCharts.length > 0 ? (
  <InlineEvidenceCharts charts={answerCard.inlineCharts} />
) : null}

<section className="space-y-4">
  {/* supplemental evidence disclosure */}
</section>
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| No inline visual evidence in chat | Answer-first chat with optional inline chart previews | Phase 20 target in milestone `v1.3` | Charts must fit the existing narrative/confidence/evidence shell, not replace it |
| Recharts 2.x `activeIndex` interaction patterns | Tooltip-driven interaction in Recharts 3 | Recharts 3.0 on 2025-06-23; current guide verified 2026-04-24 | Hover tooltips are the correct interaction primitive for this phase |
| Separate `@types/recharts` package | Built-in Recharts TypeScript definitions | Recharts guide verified 2026-04-24 | Do not add stale extra type packages |
| `hsl(var(--chart-1))` shadcn color usage in older examples | `var(--chart-1)` token usage in current shadcn chart docs | shadcn chart docs updated for Recharts v3 | Add `--chart-*` tokens to `globals.css` and reference `var(--color-KEY)` in chart series |

**Deprecated/outdated:**
- `activeIndex`-driven hover state on Recharts charts: removed in Recharts v3; use Tooltip-driven interaction.
- Installing `@types/recharts`: unnecessary; current Recharts ships its own types.
- Older shadcn chart color-token syntax using `hsl(var(--chart-1))`: current docs call for `var(--chart-1)`.

## Open Questions

1. **Exact focal-series rule when multiple tickers are present**
   - What we know: `features_csv` and `peer_signals_csv` can support either ticker-vs-ticker series or focal-vs-peer-median series.
   - What's unclear: whether product wants the first input ticker treated as the focal series for multi-ticker runs.
   - Recommendation: for Phase 20, use actual ticker series only when there are at most 3 readable series; otherwise collapse the peer set into `Peer median`.

2. **Exact metric tie-break when several deterministic candidates are equally strong**
   - What we know: the context leaves this heuristic to discretion.
   - What's unclear: whether metric priority should prefer goal preferences, strongest signal score, or a fixed domain order.
   - Recommendation: use deterministic priority order: explicit goal priority metric if present, then strongest eligible signal row, then fixed metric order (`revenue_growth_qoq`, `revenue`, `net_margin`, `current_ratio`, `debt_to_assets`).

3. **Whether captions should include exact-jump links in Phase 20**
   - What we know: the user asked for charts plus short captions, not a second evidence row inside the chart card.
   - What's unclear: whether a visible “Open source” affordance belongs in the first release.
   - Recommendation: keep captions text-only in Phase 20, but include `source_artifact_roles` in the contract so a later phase can add exact jumps without changing the backend selection logic.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Node.js | Frontend install, build, and tests | ✓ | `v24.9.0` | CI uses Node 20; both satisfy repo needs |
| npm | `recharts` install and Vitest/lint/build scripts | ✓ | `11.6.0` | — |
| npx | `shadcn@latest add chart` scaffold step | ✓ | `11.6.0` | Manual copy of `components/ui/chart.tsx` from official docs if CLI is blocked |
| Python 3 | Backend unit/API tests | ✓ | `3.11.0` | Use CI or a 3.12 env for final verification; repo target is Python 3.12+ |
| `pytest` | Backend unit/API tests | ✓ | `8.4.2` | — |
| `python` alias | Local shorthand in some commands | ✗ | — | Use `python3` locally |

**Missing dependencies with no fallback:**
- None.

**Missing dependencies with fallback:**
- Local `python` alias is absent; use `python3`.
- Local Python is `3.11.0`, below the repo’s documented `3.12+` target; final backend verification should run in CI or a 3.12 environment.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | `pytest 8.4.2` + `Vitest 2.1.9` |
| Config file | Backend: none detected; Frontend: `frontend/vitest.config.ts` |
| Quick run command | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q && (cd frontend && npm test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/lib/chat-run-history.test.ts src/actions/runs.test.ts)` |
| Full suite command | `python3 -m pytest tests/ -q --tb=short && (cd frontend && npm run lint && npm run build && npm test)` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHRT-01 | Chat answer renders inline charts only when backend preview data is present, and keeps them above supplemental evidence | frontend component/unit | `cd frontend && npm test -- src/components/chat-shell/chat-message-list.test.tsx src/lib/chat-run-history.test.ts src/actions/runs.test.ts` | ✅ |
| CHRT-02 | API exposes explicit safe chart previews sourced from deterministic artifacts/metrics, not frontend inference | backend unit + API | `python3 -m pytest tests/test_run_transparency_builders.py tests/test_traceability_summary.py tests/test_sprint3_transparency_api.py -q` | ✅ |
| CHRT-03 | Every rendered chart includes a short caption tied to the answer context | frontend view-model + renderer | `cd frontend && npm test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx` | ✅ |

### Sampling Rate
- **Per task commit:** run the focused backend and frontend commands above.
- **Per wave merge:** run the full backend suite plus frontend lint/build/tests.
- **Phase gate:** full suite green before `/gsd:verify-work`.

### Wave 0 Gaps
- [ ] `tests/test_inline_chart_preview.py` — new deterministic backend builder coverage for chart selection, row caps, peer/trend gating, and caption generation
- [ ] Extend `tests/test_run_transparency_builders.py` — assert `inline_charts` parsing/projection and empty-safe fallback behavior
- [ ] Extend `tests/test_traceability_summary.py` — assert chart previews are persisted under `traceability.report`
- [ ] Extend `tests/test_sprint3_transparency_api.py` — assert API response includes chart previews without mutating existing payload fields
- [ ] `frontend/src/components/structured-answer/inline-evidence-charts.test.tsx` — new renderer coverage for placement, captions, responsive container class, and hover-only interaction shell
- [ ] Extend `frontend/src/lib/__tests__/run-primary-view.test.ts` — assert wire-to-view mapping defaults `inlineCharts` to `[]` and preserves answer compatibility when charts are absent

## Sources

### Primary (HIGH confidence)
- Local repo seams:
  - `frontend/src/components/chat-shell/chat-run-answer-card.tsx`
  - `frontend/src/lib/run-primary-view.ts`
  - `frontend/src/actions/runs.ts`
  - `frontend/src/lib/chat-run-history.ts`
  - `backend/schemas/run_transparency.py`
  - `backend/agents/traceability_summary.py`
  - `src/features.py`
  - `src/peer_signals.py`
  - `src/trend_breaks.py`
  - `src/findings.py`
  - `edgar_project/run_workspace.py`
  - `edgar_project/orchestration/plan_templates.py`
- Official shadcn chart docs: https://ui.shadcn.com/docs/components/radix/chart
- Official Recharts guide and API:
  - https://recharts.github.io/en-US/guide/
  - https://recharts.github.io/en-US/guide/typescript/
  - https://recharts.github.io/en-US/guide/activeIndex/
  - https://recharts.github.io/en-US/api/ResponsiveContainer/
  - https://recharts.github.io/en-US/api/Tooltip/
  - https://recharts.github.io/en-US/api/LineChart/
  - https://recharts.github.io/en-US/api/BarChart/
- npm registry verification run locally on 2026-04-24:
  - `npm view recharts version time peerDependencies --json`
  - `npm view shadcn version time --json`

### Secondary (MEDIUM confidence)
- None needed.

### Tertiary (LOW confidence)
- None.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - official shadcn/Recharts docs plus npm registry verification
- Architecture: HIGH - current repo seams, prior phase contexts, and tests all point to the same extension path
- Pitfalls: HIGH - combination of official Recharts/shadcn guidance and brownfield fixture/layout analysis

**Research date:** 2026-04-24
**Valid until:** 2026-05-24
