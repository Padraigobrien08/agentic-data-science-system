---
phase: 20-inline-charts-in-chat
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/app/globals.css
  - frontend/src/components/ui/chart.tsx
  - frontend/src/components/structured-answer/inline-evidence-charts.tsx
  - frontend/src/components/structured-answer/index.ts
  - frontend/src/components/structured-answer/types.ts
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/lib/__tests__/run-primary-view.test.ts
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
  - frontend/src/components/runs/run-inspection-panel.test.tsx
autonomous: true
requirements:
  - CHRT-01
  - CHRT-03
must_haves:
  truths:
    - "Chat can render one or two backend-authored inline charts inside the answer column when trusted previews are present."
    - "Charts sit beneath the prose answer and confidence header, and above the supplemental evidence disclosure, preserving the prose -> proof -> evidence order."
    - "The frontend maps safe chart previews into render props without inferring chart families, metrics, or data from raw payloads."
  artifacts:
    - path: frontend/src/components/ui/chart.tsx
      provides: "Local shadcn/Recharts wrapper used by the answer-specific chart renderer"
    - path: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      provides: "Answer-scoped inline chart renderer for line and grouped-bar previews"
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Frontend chart view-model derivation with default empty-chart behavior"
  key_links:
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      via: "The answer view model maps backend-safe previews into render-only chart props"
      pattern: "inlineCharts|InlineChartView"
    - from: frontend/src/components/ui/chart.tsx
      to: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      via: "shadcn chart primitives provide responsive sizing and tooltip chrome without custom SVG infrastructure"
      pattern: "ChartContainer|ChartTooltip|ChartTooltipContent"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      via: "The renderer places visual evidence between narrative prose and the supporting-evidence disclosure"
      pattern: "Visual evidence|Show supporting evidence"
---

<objective>
Install the shadcn/Recharts chart surface, map backend previews into a frontend view model, and render inline charts inside the chat answer without disturbing the answer-first layout.

Purpose: satisfy the visible chat-rendering half of `CHRT-01` and display backend-authored captions toward `CHRT-03` while keeping frontend logic render-only.
Output: chart dependency/setup, answer-scoped chart renderer, chart view-model wiring, and transcript regressions for the new placement.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
@.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
@.planning/phases/20-inline-charts-in-chat/20-VALIDATION.md
@.planning/phases/20-inline-charts-in-chat/20-UI-SPEC.md
@.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-01-PLAN.md
@/Users/padraigobrien/.agents/skills/shadcn-ui/SKILL.md
@frontend/components.json
@frontend/package.json
@frontend/src/app/globals.css
@frontend/src/lib/run-primary-view.ts
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@frontend/src/lib/__tests__/run-primary-view.test.ts
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/components/runs/run-inspection-panel.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add the shadcn/Recharts chart surface and answer-scoped renderer</name>
  <files>frontend/package.json
frontend/package-lock.json
frontend/src/app/globals.css
frontend/src/components/ui/chart.tsx
frontend/src/components/structured-answer/inline-evidence-charts.tsx
frontend/src/components/structured-answer/index.ts
frontend/src/components/structured-answer/types.ts</files>
  <read_first>.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
.planning/phases/20-inline-charts-in-chat/20-UI-SPEC.md
/Users/padraigobrien/.agents/skills/shadcn-ui/SKILL.md
frontend/components.json
frontend/package.json
frontend/src/app/globals.css
frontend/src/components/ui/popover.tsx
frontend/src/components/structured-answer/index.ts
frontend/src/components/structured-answer/types.ts</read_first>
  <behavior>
    - The chart stack must use `recharts` plus the local shadcn `chart` wrapper rather than custom SVG or browser-side CSV parsing.
    - The answer-specific renderer must support only `line` and `grouped_bar` previews per D-10, D-11, and D-13.
    - The cards must keep explicit height, neutral chrome, hover tooltips only, and no filters or toggles per D-15 and D-16.
  </behavior>
  <action>In `frontend/`, add `recharts@^3.8.1` to `package.json` and update `package-lock.json`. If `frontend/src/components/ui/chart.tsx` does not exist, create it using the current shadcn `chart` scaffold semantics from the local shadcn setup rather than inventing a new wrapper. In `frontend/src/app/globals.css`, add `--chart-1`, `--chart-2`, `--chart-3`, and `--chart-4` to the light and dark CSS-variable blocks using the Phase 20 palette from `20-UI-SPEC.md`. Create `frontend/src/components/structured-answer/inline-evidence-charts.tsx` as the answer-specific renderer. It must accept render-ready chart props and render one `Visual evidence` overline, up to two vertically stacked cards per D-02, line charts via `LineChart` + `Line`, grouped peer charts via `BarChart` + `Bar`, optional deterministic markers via `ReferenceDot` or `ReferenceLine`, explicit plot heights (`min-h-[220px]` mobile and `min-h-[240px]` desktop), and captions below the plot. Export the new renderer from `frontend/src/components/structured-answer/index.ts`, and add any shared prop types needed in `frontend/src/components/structured-answer/types.ts`. Do not add pie, donut, area-fill, metric-switch, or side-by-side dashboard layouts per D-03, D-13, and D-16.</action>
  <acceptance_criteria>`frontend/package.json` contains `recharts`.
`frontend/src/components/ui/chart.tsx` exists.
`frontend/src/app/globals.css` contains `--chart-1`.
`frontend/src/app/globals.css` contains `--chart-2`.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` exists.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` contains `Visual evidence`.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` contains `LineChart`.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` contains `BarChart`.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` contains `ChartTooltip`.
`cd frontend && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run build</automated>
  </verify>
  <done>The repo now has the chart dependency, local shadcn chart wrapper, chart color tokens, and a dedicated inline chart renderer ready for answer-card wiring.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Map safe chart previews into the answer view model and place charts inside chat</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/lib/__tests__/run-primary-view.test.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</files>
  <read_first>.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
.planning/phases/20-inline-charts-in-chat/20-UI-SPEC.md
.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-01-PLAN.md
frontend/src/lib/api/types.ts
frontend/src/lib/run-primary-view.ts
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/components/structured-answer/inline-evidence-charts.tsx
frontend/src/lib/__tests__/run-primary-view.test.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</read_first>
  <behavior>
    - The frontend must render only backend-authored `inline_charts` previews and must not infer chart types or data from prose or raw payloads per D-04 and D-05.
    - Charts must appear beneath the narrative prose and confidence header, and above the supplemental evidence disclosure per D-07, D-08, and D-09.
    - Empty preview lists must omit the section entirely so charts remain evidentiary support rather than default decoration per D-01 and D-03.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add exact chart view-model types named `InlineChartSeriesView`, `InlineChartMarkerView`, and `InlineChartView`, plus an `inlineCharts: InlineChartView[]` field on both `PrimaryAnswerView` and `ChatAnswerCardView`. Add a mapper that converts `transparency.inline_charts ?? []` into render-ready chart props and defaults to `[]` when the API omits the field, so downstream renderers never need null checks. The mapper must trust only the bounded preview contract from Plan 01 and reject unknown `kind` values or rows with no series data instead of inferring replacements. In `buildChatAnswerCardView(...)`, pass `inlineCharts` through unchanged. In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, render `InlineEvidenceCharts` between the answer prose/support note block and the supplemental evidence disclosure so the final order is prose, visual proof, then deeper evidence per D-07, D-08, and D-09. Do not render the chart section when `answerCard.inlineCharts.length === 0`. Update `frontend/src/lib/__tests__/run-primary-view.test.ts` to assert safe preview mapping and `[]` defaults. Update `frontend/src/components/chat-shell/chat-message-list.test.tsx` and `frontend/src/components/chat-shell/chat-shell.test.tsx` to assert the `Visual evidence` section appears before `Show supporting evidence` when chart previews exist. Update `frontend/src/components/runs/run-inspection-panel.test.tsx` fixtures with `inlineCharts: []` so the shared view-model type remains explicit even though Phase 20 charts stay chat-only.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains `type InlineChartView`.
`frontend/src/lib/run-primary-view.ts` contains `inlineCharts: InlineChartView[]`.
`frontend/src/lib/run-primary-view.ts` contains `transparency.inline_charts`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Visual evidence`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Show supporting evidence`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `inlineCharts`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Visual evidence`.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains `Visual evidence`.
`frontend/src/components/runs/run-inspection-panel.test.tsx` contains `inlineCharts`.
`cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx</automated>
  </verify>
  <done>Chat answers now map backend-safe chart previews into a render-only view model and place charts in the correct narrative-first slot.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx` after both tasks land.
</verification>

<success_criteria>
Phase 20 Wave 2 is complete when chat can render backend-authored inline charts inside the answer column with shadcn/Recharts, the view-model seam stays render-only, and the prose -> proof -> evidence order remains intact.
</success_criteria>

<output>
After completion, create `.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-02-SUMMARY.md`
</output>
