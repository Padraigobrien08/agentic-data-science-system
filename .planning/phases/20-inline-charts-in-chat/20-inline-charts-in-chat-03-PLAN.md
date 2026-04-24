---
phase: 20-inline-charts-in-chat
plan: 03
type: execute
wave: 3
depends_on:
  - 01
  - 02
files_modified:
  - backend/agents/inline_chart_preview.py
  - tests/test_traceability_summary.py
  - frontend/src/lib/run-primary-view.ts
  - frontend/src/components/structured-answer/inline-evidence-charts.tsx
  - frontend/src/components/chat-shell/chat-run-answer-card.tsx
  - frontend/src/lib/__tests__/run-primary-view.test.ts
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/components/chat-shell/chat-shell.test.tsx
  - frontend/src/components/runs/run-inspection-panel.test.tsx
autonomous: true
requirements:
  - CHRT-01
  - CHRT-02
  - CHRT-03
must_haves:
  truths:
    - "Only strong deterministic cases keep charts in the answer; weak or malformed previews do not dilute the prose-first reading flow."
    - "Every rendered chart includes one short caption explaining what it shows and why it matters."
    - "When preview data is dropped during frontend mapping, chat either omits the section cleanly or shows one slim fallback notice instead of breaking the answer card."
  artifacts:
    - path: backend/agents/inline_chart_preview.py
      provides: "Strong-case chart gating and deterministic caption generation"
    - path: frontend/src/lib/run-primary-view.ts
      provides: "Fallback-safe chart mapping and notice handling for malformed previews"
    - path: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      provides: "Final inline chart rendering and fallback notice behavior"
  key_links:
    - from: backend/agents/inline_chart_preview.py
      to: frontend/src/lib/run-primary-view.ts
      via: "Only strong backend previews survive into the answer view model, and each includes a caption"
      pattern: "caption|chart_id|kind"
    - from: frontend/src/lib/run-primary-view.ts
      to: frontend/src/components/structured-answer/inline-evidence-charts.tsx
      via: "Malformed previews downgrade to a fallback notice instead of crashing the renderer"
      pattern: "inlineChartNotice|Chart preview unavailable"
    - from: frontend/src/components/chat-shell/chat-run-answer-card.tsx
      to: frontend/src/components/chat-shell/chat-message-list.test.tsx
      via: "Transcript tests lock final chart placement, caption rendering, omission, and fallback behavior"
      pattern: "Visual evidence|Chart preview unavailable|Show supporting evidence"
---

<objective>
Harden the inline chart experience so only strong deterministic cases render, every chart shows a concise caption, fallback behavior is deliberate, and the final regression/build gate is green.

Purpose: finish `CHRT-01`, `CHRT-02`, and `CHRT-03` with strong-case gating, caption discipline, and failure-safe rendering that preserves trust.
Output: tightened backend gating and caption copy, frontend fallback handling for dropped previews, and full phase validation including production build.
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
@.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-02-PLAN.md
@backend/agents/inline_chart_preview.py
@frontend/src/lib/run-primary-view.ts
@frontend/src/components/structured-answer/inline-evidence-charts.tsx
@frontend/src/components/chat-shell/chat-run-answer-card.tsx
@tests/test_traceability_summary.py
@frontend/src/lib/__tests__/run-primary-view.test.ts
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
@frontend/src/components/runs/run-inspection-panel.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Tighten strong-case gating and backend-authored caption generation</name>
  <files>backend/agents/inline_chart_preview.py
tests/test_traceability_summary.py</files>
  <read_first>.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
.planning/phases/20-inline-charts-in-chat/20-UI-SPEC.md
.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-01-PLAN.md
backend/agents/inline_chart_preview.py
src/peer_signals.py
src/trend_breaks.py
tests/test_traceability_summary.py</read_first>
  <behavior>
    - Only strong deterministic cases should survive into `inline_charts` per D-01 and D-03.
    - Every surviving preview must carry one short backend-authored caption per D-14.
    - Weak peer coverage, short history, or malformed rows must suppress the chart instead of degrading answer trust per D-06.
  </behavior>
  <action>In `backend/agents/inline_chart_preview.py`, tighten the gating introduced in Plan 01 so charts only survive strong support paths. For line charts, require either `trend_signal_type == "strong_shift"` or `trend_score >= 2.0`, `short_history_flag == False`, and at least four focal periods for the selected metric. For grouped peer charts, require `peer_coverage == "full"`, `peer_alert in {"extreme_high", "extreme_low"}`, at least two peer firms beyond the focal company, and at least two recent common periods. Keep the `1-2` chart cap and trend-before-peer ordering per D-02. Add deterministic caption builders that emit exactly one short sentence per chart, target roughly `90-160` characters, and use a stable two-clause pattern: first clause says what the visual shows, second clause says why it matters. The caption logic must stay artifact-derived and must not inspect narrative prose or raw frontend payloads per D-04 and D-05. Suppress any candidate whose caption or rows cannot be built cleanly. Extend `tests/test_traceability_summary.py` with explicit strong-case and weak-case fixtures so the suite proves strong trends survive, weak peer coverage is filtered, the chart cap stays at two, and every surviving preview includes a non-empty caption.</action>
  <acceptance_criteria>`backend/agents/inline_chart_preview.py` contains `caption`.
`backend/agents/inline_chart_preview.py` contains `trend_score >= 2.0` or an equivalent strong-case threshold.
`backend/agents/inline_chart_preview.py` contains `peer_coverage`.
`backend/agents/inline_chart_preview.py` contains `peer_alert`.
`tests/test_traceability_summary.py` contains `caption`.
`tests/test_traceability_summary.py` contains `peer_coverage`.
`tests/test_traceability_summary.py` contains `strong_shift`.
`python3 -m pytest tests/test_traceability_summary.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_traceability_summary.py -q --tb=short</automated>
  </verify>
  <done>The backend now emits charts only for strong deterministic cases, and every surviving preview includes a concise caption.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add fallback-safe chart mapping and run the final regression/build gate</name>
  <files>frontend/src/lib/run-primary-view.ts
frontend/src/components/structured-answer/inline-evidence-charts.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/lib/__tests__/run-primary-view.test.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</files>
  <read_first>.planning/phases/20-inline-charts-in-chat/20-CONTEXT.md
.planning/phases/20-inline-charts-in-chat/20-RESEARCH.md
.planning/phases/20-inline-charts-in-chat/20-VALIDATION.md
.planning/phases/20-inline-charts-in-chat/20-UI-SPEC.md
.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-02-PLAN.md
frontend/src/lib/run-primary-view.ts
frontend/src/components/structured-answer/inline-evidence-charts.tsx
frontend/src/components/chat-shell/chat-run-answer-card.tsx
frontend/src/lib/__tests__/run-primary-view.test.ts
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/components/chat-shell/chat-shell.test.tsx
frontend/src/components/runs/run-inspection-panel.test.tsx</read_first>
  <behavior>
    - Empty chart lists must omit the section entirely so the answer does not gain decorative empty chrome per D-01 and D-03.
    - Malformed or unsupported previews must degrade to one slim fallback notice rather than throwing or rendering broken charts.
    - Final transcript behavior must preserve the prose -> visual proof -> supplemental evidence hierarchy while keeping tooltips lightweight per D-07, D-08, D-09, and D-15.
  </behavior>
  <action>In `frontend/src/lib/run-primary-view.ts`, add an exact field named `inlineChartNotice: string | null` to `PrimaryAnswerView` and `ChatAnswerCardView`. When `transparency.inline_charts` is absent or `[]`, keep `inlineCharts` as `[]` and `inlineChartNotice` as `null`. When `transparency.inline_charts` is present but every preview is dropped during mapping because of an unknown kind, missing caption, empty rows, or series/row mismatch, set `inlineChartNotice` to the exact UI-SPEC copy `Chart preview unavailable. Read the answer text, then open supporting evidence or trace to inspect the underlying run artifacts.`. In `frontend/src/components/structured-answer/inline-evidence-charts.tsx`, render captions below the plot area for valid charts, render one slim fallback notice when `inlineChartNotice` is set, and render nothing when both values are empty. In `frontend/src/components/chat-shell/chat-run-answer-card.tsx`, keep the chart section between the narrative block and the supplemental evidence disclosure even in the fallback notice case. Update `frontend/src/lib/__tests__/run-primary-view.test.ts`, `frontend/src/components/chat-shell/chat-message-list.test.tsx`, and `frontend/src/components/chat-shell/chat-shell.test.tsx` so they assert supported previews show captions, malformed previews show the exact fallback notice, and empty previews omit the section. Update `frontend/src/components/runs/run-inspection-panel.test.tsx` fixtures with `inlineChartNotice: null`. Finish by running the full Phase 20 validation gate from `20-VALIDATION.md`: backend transparency tests, frontend chart/view-model/transcript tests, and `npm run build`.</action>
  <acceptance_criteria>`frontend/src/lib/run-primary-view.ts` contains `inlineChartNotice: string | null`.
`frontend/src/lib/run-primary-view.ts` contains `Chart preview unavailable. Read the answer text`.
`frontend/src/components/structured-answer/inline-evidence-charts.tsx` contains `Chart preview unavailable. Read the answer text`.
`frontend/src/components/chat-shell/chat-run-answer-card.tsx` contains `Show supporting evidence`.
`frontend/src/lib/__tests__/run-primary-view.test.ts` contains `inlineChartNotice`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains `Chart preview unavailable`.
`frontend/src/components/chat-shell/chat-shell.test.tsx` contains `Chart preview unavailable`.
`frontend/src/components/runs/run-inspection-panel.test.tsx` contains `inlineChartNotice`.
`python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx && npm run build` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx && npm run build</automated>
  </verify>
  <done>The chart experience now fails safely, captions are visible, weak cases stay out of chat, and the full phase validation/build gate is green.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_traceability_summary.py tests/test_run_transparency_builders.py tests/test_sprint3_transparency_api.py -q --tb=short && cd frontend && npm run test -- src/lib/__tests__/run-primary-view.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx src/components/runs/run-inspection-panel.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 20 is complete when only strong deterministic cases render charts, every rendered chart includes a concise caption, malformed previews degrade gracefully, and the backend/frontend regression plus production build gate passes.
</success_criteria>

<output>
After completion, create `.planning/phases/20-inline-charts-in-chat/20-inline-charts-in-chat-03-SUMMARY.md`
</output>
