---
phase: 08-summary-first-large-trace-views
plan: 03
type: execute
wave: 3
depends_on:
  - "08-01"
  - "08-02"
files_modified:
  - frontend/src/lib/api/runs.ts
  - frontend/src/lib/api/types.ts
  - frontend/src/components/trace/run-trace-collection-panel.tsx
  - frontend/src/components/trace/trace-raw-detail-sheet.tsx
  - frontend/src/components/runs/run-step-trace.tsx
  - frontend/src/components/transparency/model-call-summary-card.tsx
  - frontend/src/components/trace/artifact-detail-panel.tsx
  - frontend/src/components/runs/run-step-trace.test.tsx
  - frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx
  - frontend/src/components/trace/run-trace-summary-view.test.tsx
autonomous: true
requirements:
  - TRACE-02
  - TRACE-03
must_haves:
  truths:
    - "Raw step and model-call payloads are fetched only after an explicit per-item action and only for the selected item."
    - "The privileged raw view stays local to one sheet or inline pane, while artifact preview continues to use app-owned routes and linked timeline cues."
    - "Summary-first rendering remains the default path and regression coverage proves the old page-wide raw inspector behavior is no longer required for normal trace inspection."
  artifacts:
    - path: frontend/src/lib/api/runs.ts
      provides: "Item-scoped frontend fetch helpers for step and model-call raw detail"
    - path: frontend/src/components/trace/trace-raw-detail-sheet.tsx
      provides: "One-at-a-time raw detail surface for privileged debug drill-down"
    - path: frontend/src/components/runs/run-step-trace.tsx
      provides: "Step summary rows that keep JSON hidden until explicit inspection"
    - path: frontend/src/components/transparency/model-call-summary-card.tsx
      provides: "Model-call summary cards with bounded raw payload expansion"
    - path: frontend/src/components/runs/run-step-trace.test.tsx
      provides: "Regression coverage proving step JSON stays collapsed until explicitly fetched"
  key_links:
    - from: frontend/src/lib/api/runs.ts
      to: frontend/src/components/trace/trace-raw-detail-sheet.tsx
      via: "the raw detail surface fetches one step or model call at a time from the new item routes"
      pattern: "getRunStep|getRunModelCall|includePayloads"
    - from: frontend/src/components/runs/run-step-trace.tsx
      to: frontend/src/components/trace/run-trace-collection-panel.tsx
      via: "step rows surface explicit inspect actions and timeline-linked cues instead of dumping JSON inline by default"
      pattern: "Inspect step details|Open raw payload"
    - from: frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx
      to: frontend/src/components/transparency/model-call-summary-card.tsx
      via: "tests lock payload omission by default and bounded raw display after one explicit action"
      pattern: "Payloads omitted|Open raw payload"
---

<objective>
Finish Phase 08 by wiring per-item raw expansion, keeping artifact drill-down bounded, and hardening regressions for the summary-first trace flow.

Purpose: satisfy the UI and bounded-debug side of `TRACE-03` while locking the summary-first behavior introduced in the earlier waves.
Output: item-scoped frontend raw fetch helpers, one-at-a-time detail surfaces, and focused frontend regressions for raw expansion behavior.
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
@.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md
@.planning/phases/08-summary-first-large-trace-views/08-RESEARCH.md
@.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
@.planning/phases/08-summary-first-large-trace-views/08-UI-SPEC.md
@.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-01-PLAN.md
@.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-02-PLAN.md
@frontend/src/lib/api/runs.ts
@frontend/src/lib/api/types.ts
@frontend/src/components/runs/run-step-trace.tsx
@frontend/src/components/transparency/model-call-summary-card.tsx
@frontend/src/components/trace/artifact-detail-panel.tsx
@frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx

<interfaces>
From `frontend/src/lib/api/runs.ts` after Plan 02:
```ts
export async function getRunTraceSummary(...)
export async function listRunSteps(...)
export async function listRunArtifacts(...)
export async function listRunModelCalls(...)
```

From `backend/api/routes/runs.py` after Plan 01:
```python
@router.get("/{run_id}/steps/{step_id}", response_model=RunStepDetailItem)
@router.get("/{run_id}/model-calls/{model_call_id}", response_model=ModelCallApiItem)
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Wire per-item raw fetch helpers and a one-at-a-time detail surface</name>
  <files>frontend/src/lib/api/runs.ts
frontend/src/lib/api/types.ts
frontend/src/components/trace/run-trace-collection-panel.tsx
frontend/src/components/trace/trace-raw-detail-sheet.tsx
frontend/src/components/runs/run-step-trace.tsx
frontend/src/components/transparency/model-call-summary-card.tsx
frontend/src/components/trace/artifact-detail-panel.tsx</files>
  <read_first>.planning/phases/08-summary-first-large-trace-views/08-UI-SPEC.md
.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-01-PLAN.md
.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-02-PLAN.md
frontend/src/lib/api/runs.ts
frontend/src/lib/api/types.ts
frontend/src/components/trace/run-trace-collection-panel.tsx
frontend/src/components/runs/run-step-trace.tsx
frontend/src/components/transparency/model-call-summary-card.tsx
frontend/src/components/trace/artifact-detail-panel.tsx</read_first>
  <behavior>
    - Per D-05 and D-06, raw payload data is fetched only for the selected item after an explicit action and never as a page-wide mode switch.
    - Desktop default is a right-side detail sheet; narrow screens fall back to inline expansion below the selected row.
    - Only one raw detail surface may be open at a time, and artifact preview continues to rely on the application-owned artifact routes instead of storage locators.
  </behavior>
  <action>Extend `frontend/src/lib/api/types.ts` and `frontend/src/lib/api/runs.ts` with item-scoped helpers such as `getRunStep(runId, stepId, options)` and `getRunModelCall(runId, modelCallId, options)`. Create `frontend/src/components/trace/trace-raw-detail-sheet.tsx` using the approved shadcn `Sheet` pattern so one selected step or model call can open a bounded raw-detail surface at a time. Refactor `frontend/src/components/trace/run-trace-collection-panel.tsx`, `frontend/src/components/runs/run-step-trace.tsx`, and `frontend/src/components/transparency/model-call-summary-card.tsx` so summary rows render explicit labels like `Inspect step details`, `Inspect model call`, and `Open raw payload`; the raw JSON is fetched only after the user chooses one item; and non-admin or failed raw fetches show a bounded local error state instead of breaking the full page. Keep `frontend/src/components/trace/artifact-detail-panel.tsx` on the existing preview/detail route contract while surfacing linked step or phase cues back to the timeline spine.</action>
  <acceptance_criteria>`frontend/src/lib/api/runs.ts` contains `getRunStep(`.
`frontend/src/lib/api/runs.ts` contains `getRunModelCall(`.
`frontend/src/components/trace/trace-raw-detail-sheet.tsx` exists.
`frontend/src/components/runs/run-step-trace.tsx` contains `Inspect step details`.
`frontend/src/components/runs/run-step-trace.tsx` does not render `planner_tool_input_json` or `meta_json` unconditionally on the default list rows.
`frontend/src/components/transparency/model-call-summary-card.tsx` contains `Inspect model call`.
`frontend/src/components/transparency/model-call-summary-card.tsx` contains `Open raw payload`.
`frontend/src/components/trace/run-trace-collection-panel.tsx` contains one-open-at-a-time state for the raw detail surface.
`frontend/src/components/trace/artifact-detail-panel.tsx` still routes artifact preview through the app-owned artifact detail or preview experience.
`cd frontend && npm run test -- model-call-summary-card.test.tsx run-step-trace.test.tsx` passes once the tests exist.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- model-call-summary-card.test.tsx run-step-trace.test.tsx</automated>
  </verify>
  <done>Privileged raw trace inspection is now bounded to one selected item and no longer depends on bulk first-load payload hydration.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Harden frontend regressions around summary-first defaults and bounded raw expansion</name>
  <files>frontend/src/components/runs/run-step-trace.test.tsx
frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx
frontend/src/components/trace/run-trace-summary-view.test.tsx</files>
  <read_first>.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
frontend/src/components/runs/run-step-trace.tsx
frontend/src/components/transparency/model-call-summary-card.tsx
frontend/src/components/trace/run-trace-summary-view.tsx
frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx</read_first>
  <behavior>
    - Step and model-call tests prove raw JSON stays hidden until explicit interaction or an item-scoped raw fetch result is provided.
    - The summary view test proves the overview remains primary even after drill-down affordances are added.
    - Phase 08 quick validation reruns both backend and frontend coverage so the new UI still matches the backend contract and Sprint 3 transparency compatibility.
  </behavior>
  <action>Create `frontend/src/components/runs/run-step-trace.test.tsx` to assert step JSON is not rendered by default, explicit inspect actions are present, and the selected item detail surface is local rather than page-wide. Extend `frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx` to keep the payload omission note by default and cover one bounded raw-display state. Extend `frontend/src/components/trace/run-trace-summary-view.test.tsx` so collection summaries and the timeline remain visible while a detail pane is open. Finish by rerunning the full Phase 08 quick command from `08-VALIDATION.md`: `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx`.</action>
  <acceptance_criteria>`frontend/src/components/runs/run-step-trace.test.tsx` exists.
`frontend/src/components/runs/run-step-trace.test.tsx` asserts raw JSON stays hidden by default.
`frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx` contains `Open raw payload`.
`frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx` still covers `Payloads omitted`.
`frontend/src/components/trace/run-trace-summary-view.test.tsx` covers collection separation while drill-down controls exist.
`python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx</automated>
  </verify>
  <done>The summary-first trace flow and one-item raw expansion behavior are both locked by focused regression coverage.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- model-call-summary-card.test.tsx run-step-trace.test.tsx` after the raw-detail surface lands, then rerun the full quick command from `08-VALIDATION.md` once the new tests are in place.
</verification>

<success_criteria>
Phase 08 is complete once the trace page opens summary-first, raw payloads are fetched only for one selected item at a time, and regressions prove the old bulk-payload deep-dive path is no longer required for normal trace inspection.
</success_criteria>

<output>
After completion, create `.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-03-SUMMARY.md`
</output>
