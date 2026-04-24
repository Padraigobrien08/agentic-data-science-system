---
phase: 20-inline-charts-in-chat
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/agents/inline_chart_preview.py
  - backend/agents/traceability_summary.py
  - backend/schemas/run_transparency.py
  - frontend/src/lib/api/types.ts
  - tests/test_traceability_summary.py
  - tests/test_run_transparency_builders.py
  - tests/test_sprint3_transparency_api.py
autonomous: true
requirements:
  - CHRT-01
  - CHRT-02
must_haves:
  truths:
    - "Run transparency exposes at most two deterministic inline chart previews when trusted artifact data supports a visual explanation."
    - "Each preview is a bounded safe contract built from trusted artifact roles and metric outputs, not raw Recharts config or frontend inference."
    - "Weak, underspecified, or unsupported artifact cases produce `inline_charts: []` instead of speculative visuals."
  artifacts:
    - path: backend/agents/inline_chart_preview.py
      provides: "Deterministic chart candidate selection and bounded preview assembly"
    - path: backend/schemas/run_transparency.py
      provides: "Typed inline chart preview surface on run transparency"
    - path: tests/test_traceability_summary.py
      provides: "Regression coverage for traceability-level chart selection, cap, and suppression behavior"
  key_links:
    - from: backend/agents/inline_chart_preview.py
      to: backend/agents/traceability_summary.py
      via: "Traceability persists backend-authored chart previews under `report.inline_charts`"
      pattern: "build_inline_chart_previews|inline_charts"
    - from: backend/agents/traceability_summary.py
      to: backend/schemas/run_transparency.py
      via: "The safe preview is projected into `RunTransparencySummary.inline_charts`"
      pattern: "inline_charts|InlineChartPreview"
    - from: backend/schemas/run_transparency.py
      to: frontend/src/lib/api/types.ts
      via: "The frontend wire mirror matches the backend-safe chart contract exactly"
      pattern: "inline_charts|InlineChartPreview"
---

<objective>
Define the backend-safe inline chart contract and deterministic selection path before any chat renderer starts drawing charts.

Purpose: satisfy `CHRT-01` and `CHRT-02` by making chart eligibility and preview generation backend-owned, explicit, and traceable.
Output: a bounded `inline_charts` transparency contract, a deterministic chart-preview builder sourced from trusted artifacts, and backend regression coverage for selection, suppression, and API transport.
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
@backend/agents/traceability_summary.py
@backend/schemas/run_transparency.py
@frontend/src/lib/api/types.ts
@edgar_project/mcp/schemas.py
@src/peer_signals.py
@src/trend_breaks.py
@src/metric_extraction.py
@tests/test_traceability_summary.py
@tests/test_run_transparency_builders.py
@tests/test_sprint3_transparency_api.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Define the safe inline chart preview contract on run transparency</name>
  <files>backend/schemas/run_transparency.py
frontend/src/lib/api/types.ts
tests/test_run_transparency_builders.py
tests/test_sprint3_transparency_api.py</files>
  <read_first>.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
.planning/phases/20-inline-charts-in-chat/20-VALIDATION.md
backend/schemas/run_transparency.py
frontend/src/lib/api/types.ts
tests/test_run_transparency_builders.py
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - The safe transparency surface must expose typed chart previews without sending arbitrary chart-library props.
    - The contract must be expressive enough for line charts, grouped bar charts, deterministic markers, and backend-authored captions.
    - The frontend wire mirror must match the backend contract exactly so rendering can stay read-only per D-04 and D-05.
  </behavior>
  <action>In `backend/schemas/run_transparency.py`, add exact Pydantic models named `InlineChartSeriesPreview`, `InlineChartRowPreview`, `InlineChartMarkerPreview`, and `InlineChartPreview`. The contract must use exact semantic fields rather than raw Recharts config: `chart_id`, `kind`, `metric_key`, `metric_label`, `caption`, `x_axis_label`, `y_axis_label`, `value_format`, `series`, `rows`, `markers`, and `source_artifact_roles`. Restrict `kind` to `line | grouped_bar` per D-10, D-11, and D-13. Restrict `value_format` to `currency | percent | ratio | count | number`. Restrict `series[].color_token` to `chart-1 | chart-2 | chart-3 | chart-4` so the frontend can map directly to CSS tokens. Add `inline_charts: list[InlineChartPreview] = Field(default_factory=list)` to `RunTransparencySummary` and add a parser that reads `meta_json.ai_agents.traceability.report.inline_charts` while returning `[]` for absent or malformed data. In `frontend/src/lib/api/types.ts`, add matching TypeScript interfaces with the same field names and extend `RunTransparencySummary` with `inline_charts?: InlineChartPreview[] | null`. Extend `tests/test_run_transparency_builders.py` and `tests/test_sprint3_transparency_api.py` with explicit inline-chart fixtures so the builder/parser/API path locks the exact field names, empty-list fallback, and JSON transport shape. Reference D-04, D-05, D-10, D-11, D-13, and D-14 directly in comments or helper naming where that prevents ambiguity.</action>
  <acceptance_criteria>`backend/schemas/run_transparency.py` contains `class InlineChartPreview`.
`backend/schemas/run_transparency.py` contains `class InlineChartSeriesPreview`.
`backend/schemas/run_transparency.py` contains `class InlineChartRowPreview`.
`backend/schemas/run_transparency.py` contains `class InlineChartMarkerPreview`.
`backend/schemas/run_transparency.py` contains `inline_charts: list[InlineChartPreview]`.
`frontend/src/lib/api/types.ts` contains `export interface InlineChartPreview`.
`frontend/src/lib/api/types.ts` contains `inline_charts?: InlineChartPreview[] | null`.
`tests/test_run_transparency_builders.py` contains `inline_charts`.
`tests/test_sprint3_transparency_api.py` contains `inline_charts`.
`python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short</automated>
  </verify>
  <done>The run-transparency seam now carries a bounded inline-chart contract that the frontend can render without inference.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build deterministic chart selection and persist backend-authored previews</name>
  <files>backend/agents/inline_chart_preview.py
backend/agents/traceability_summary.py
tests/test_traceability_summary.py</files>
  <read_first>.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
.planning/phases/20-inline-charts-in-chat/20-VALIDATION.md
backend/agents/traceability_summary.py
edgar_project/mcp/schemas.py
src/peer_signals.py
src/trend_breaks.py
src/metric_extraction.py
tests/test_traceability_summary.py</read_first>
  <behavior>
    - Chart selection must stay deterministic and artifact-backed per D-01, D-04, D-05, and D-06.
    - The backend must emit at most one trend line chart and one grouped peer bar chart, capped to two total previews per D-02.
    - Marker overlays may appear only when the underlying trend artifact already identifies deterministic strong-shift rows per D-12.
  </behavior>
  <action>Create `backend/agents/inline_chart_preview.py` with a top-level helper named `build_inline_chart_previews(artifact_paths: dict[str, str], *, max_charts: int = 2) -> list[dict[str, Any]]`. Read trusted local artifact paths from `orch_out.artifact_paths` using the exact role keys `features_csv`, `trend_break_signals_csv`, and `peer_signals_csv` from `edgar_project.mcp.schemas`. Use `pandas.read_csv` and `sort_period_key` from `src.metric_extraction` so period ordering stays deterministic. Build at most one `line` chart candidate and at most one `grouped_bar` chart candidate in that order. For the trend line path per D-01 and D-10, select the highest-signal trend row where `trend_signal_type in {"strong_shift", "moderate_shift"}`, `short_history_flag == False`, `history_points >= 4`, and the same focal metric has at least four non-null periods in `features_csv`; create markers only from same-metric rows with `trend_signal_type == "strong_shift"` per D-12. For the peer comparison path per D-01 and D-11, require `peer_coverage == "full"`, `peer_alert in {"extreme_high", "extreme_low"}`, at least two peer firms beyond the focal company, and at least two recent common periods in `features_csv`; compute a focal-company series and a peer-median series across up to the three most recent common periods. Generate deterministic short captions and stable `chart_id` values from the selected metric and chart family, set `source_artifact_roles` with the exact role keys used, and suppress any candidate that cannot satisfy the contract rather than emitting partial or guessed data. In `backend/agents/traceability_summary.py`, call `build_inline_chart_previews(...)` inside `build_runtime_traceability_bundle(...)` and persist the resulting list at `full["report"]["inline_charts"]`. Extend `tests/test_traceability_summary.py` with explicit temp-CSV cases covering one eligible trend chart, one eligible peer chart, the two-chart cap, and suppression when peer coverage or history is insufficient. Reference D-01, D-02, D-04, D-05, D-06, D-10, D-11, and D-12 directly in helper naming or inline comments where it clarifies the gating logic.</action>
  <acceptance_criteria>`backend/agents/inline_chart_preview.py` exists.
`backend/agents/inline_chart_preview.py` contains `def build_inline_chart_previews(`.
`backend/agents/inline_chart_preview.py` contains `ARTIFACT_KEY_FEATURES`.
`backend/agents/inline_chart_preview.py` contains `ARTIFACT_KEY_PEER_SIGNALS`.
`backend/agents/inline_chart_preview.py` contains `ARTIFACT_KEY_TREND_BREAKS`.
`backend/agents/traceability_summary.py` contains `inline_charts`.
`tests/test_traceability_summary.py` contains `inline_charts`.
`tests/test_traceability_summary.py` contains `grouped_bar`.
`tests/test_traceability_summary.py` contains `line`.
`python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short</automated>
  </verify>
  <done>The backend now decides when charts are justified, emits only bounded trusted previews, and exposes them through the safe transparency seam.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short` after both tasks land.
</verification>

<success_criteria>
Phase 20 Wave 1 is complete when the backend owns inline chart eligibility, run transparency carries a typed `inline_charts` preview, and weak artifact cases suppress charts instead of generating speculative visuals.
</success_criteria>

<output>
After completion, create `.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-01-SUMMARY.md`
</output>
