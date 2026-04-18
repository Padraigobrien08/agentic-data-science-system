---
phase: 08-summary-first-large-trace-views
plan: 02
type: execute
wave: 2
depends_on:
  - "08-01"
files_modified:
  - frontend/package.json
  - frontend/package-lock.json
  - frontend/src/lib/api/runs.ts
  - frontend/src/lib/api/types.ts
  - frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
  - frontend/src/components/trace/agentic-trace-view.tsx
  - frontend/src/components/trace/run-trace-summary-view.tsx
  - frontend/src/components/trace/run-trace-collection-panel.tsx
  - frontend/src/components/trace/deep-dive-layout.tsx
  - frontend/src/components/trace/run-trace-jump-nav.tsx
  - frontend/src/components/trace/run-trace-summary-view.test.tsx
autonomous: true
requirements:
  - TRACE-01
  - TRACE-02
must_haves:
  truths:
    - "The trace page first render is SSR-driven by the new typed trace shell and one bounded active collection instead of `include_payloads=true` requests."
    - "The active collection and its search or filter or pagination state live in URL search params so large trace navigation stays shareable and server-driven."
    - "The UI follows the approved Phase 08 contract: overview and timeline first, separate collection summaries second, one primary content column third."
  artifacts:
    - path: frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
      provides: "Summary-first SSR trace route wired to the new backend contract"
    - path: frontend/src/lib/api/runs.ts
      provides: "Typed trace shell and bounded collection API helpers"
    - path: frontend/src/components/trace/run-trace-summary-view.tsx
      provides: "Overview-first trace surface aligned with the approved UI contract"
    - path: frontend/src/components/trace/run-trace-collection-panel.tsx
      provides: "Separate steps or artifacts or model-calls navigation with URL-backed state"
    - path: frontend/src/components/trace/run-trace-summary-view.test.tsx
      provides: "Frontend regression coverage for overview-first rendering and collection separation"
  key_links:
    - from: frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
      to: frontend/src/lib/api/runs.ts
      via: "server component fetches the typed trace shell plus the active bounded collection"
      pattern: "getRunTraceSummary|collection|searchParams"
    - from: frontend/src/components/trace/run-trace-summary-view.tsx
      to: .planning/phases/08-summary-first-large-trace-views/08-UI-SPEC.md
      via: "layout, copy, and component choices follow the approved summary-first UI contract"
      pattern: "Inspect step details|No trace details yet|Trace details couldn't load"
    - from: frontend/src/components/trace/run-trace-summary-view.test.tsx
      to: frontend/src/components/trace/run-trace-summary-view.tsx
      via: "tests lock overview-first reading order, collection separation, and approved empty/error copy"
      pattern: "Steps|Artifacts|Model calls"
---

<objective>
Rebuild the trace page around the new backend shell: SSR summary-first, URL-backed collection navigation, and a visually restrained operator workflow.

Purpose: satisfy the main product-facing part of `TRACE-01` and `TRACE-02` once the backend trace contract exists.
Output: typed frontend API helpers, a summary-first trace route, and a new overview/collection UI aligned to the approved shadcn-based contract.
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
@frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx
@frontend/src/lib/api/runs.ts
@frontend/src/lib/api/types.ts
@frontend/src/components/trace/agentic-trace-view.tsx
@frontend/src/components/trace/run-trace-experience.tsx
@frontend/src/components/trace/deep-dive-layout.tsx
@frontend/src/components/trace/run-trace-jump-nav.tsx
@frontend/src/components/transparency/step-status-timeline.tsx

<interfaces>
From `frontend/src/lib/api/runs.ts`:
```ts
export async function getRun(runId: string, options?: boolean | RunFetchOptions): Promise<AnalysisRunDetail>
export async function listRunSteps(runId: string, options?: boolean | RunFetchOptions): Promise<RunStepDetail[]>
export async function listRunArtifacts(runId: string): Promise<ArtifactMetadata[]>
export async function listRunModelCalls(runId: string, includePayloads: boolean): Promise<ModelCallApiItem[]>
```

From `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`:
```ts
export default async function RunTracePage({ params }: { params: Promise<{ projectId: string; runId: string }> })
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add typed frontend helpers and URL-backed trace query state</name>
  <files>frontend/src/lib/api/runs.ts
frontend/src/lib/api/types.ts
frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx</files>
  <read_first>.planning/phases/08-summary-first-large-trace-views/08-RESEARCH.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
.planning/phases/08-summary-first-large-trace-views/08-UI-SPEC.md
.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-01-PLAN.md
frontend/src/lib/api/runs.ts
frontend/src/lib/api/types.ts
frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx</read_first>
  <behavior>
    - The trace page receives `searchParams` and treats the URL as the source of truth for active collection, search text, filters, and pagination.
    - The first render stops calling `getRun(... includePayloads: true)` and `listRunSteps(... includePayloads: true)` altogether.
    - The server component loads the typed trace shell plus only the active bounded collection needed for the current view.
  </behavior>
  <action>Extend `frontend/src/lib/api/types.ts` with typed mirrors for the new backend contract: `RunTraceShell`, collection summary/preview types, and query-param helper types for steps, artifacts, and model calls. Extend `frontend/src/lib/api/runs.ts` with exact helpers for the new backend routes, such as `getRunTraceSummary(runId, options?)`, plus query-aware collection helpers for steps, artifacts, and model calls. Then update `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` to accept `searchParams`, normalize the active collection and bounded query state on the server, call the new typed helpers, preserve the existing 401 and 404 behavior, and stop requesting raw run or step payloads on the first load.</action>
  <acceptance_criteria>`frontend/src/lib/api/types.ts` contains `RunTraceShell`.
`frontend/src/lib/api/types.ts` contains a collection-key type for `steps`, `artifacts`, and `modelCalls` or `model-calls`.
`frontend/src/lib/api/runs.ts` contains `getRunTraceSummary(`.
`frontend/src/lib/api/runs.ts` contains bounded collection helpers beyond the current `listRunSteps`, `listRunArtifacts`, and `listRunModelCalls`.
`frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` accepts `searchParams`.
`frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` no longer contains `includePayloads: true`.
`frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` no longer fetches all three collections unconditionally in one `Promise.all`.
`frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` contains the new typed trace-shell helper.
`cd frontend && npm run test -- run-trace-summary-view.test.tsx` passes once the summary view test exists.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- run-trace-summary-view.test.tsx</automated>
  </verify>
  <done>The trace route is now query-driven and summary-first at the data-fetching boundary.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Build the approved overview-first trace UI with separate collection navigation</name>
  <files>frontend/package.json
frontend/package-lock.json
frontend/src/components/trace/agentic-trace-view.tsx
frontend/src/components/trace/run-trace-summary-view.tsx
frontend/src/components/trace/run-trace-collection-panel.tsx
frontend/src/components/trace/deep-dive-layout.tsx
frontend/src/components/trace/run-trace-jump-nav.tsx
frontend/src/components/trace/run-trace-summary-view.test.tsx</files>
  <read_first>.planning/phases/08-summary-first-large-trace-views/08-UI-SPEC.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
frontend/package.json
frontend/src/components/trace/agentic-trace-view.tsx
frontend/src/components/trace/run-trace-experience.tsx
frontend/src/components/trace/deep-dive-layout.tsx
frontend/src/components/trace/run-trace-jump-nav.tsx
frontend/src/components/transparency/step-status-timeline.tsx</read_first>
  <behavior>
    - Per the approved UI contract, the first visible surface must answer what happened in the run before exposing the dense technical inspector.
    - Steps, artifacts, and model calls remain clearly separate collections, with the step timeline acting as the primary spine and jump target.
    - The UI uses the official shadcn `new-york` component patterns for restrained cards, badges, tabs, inputs, separators, and skeletons instead of decorative dashboard collage elements.
  </behavior>
  <action>Install or add the official shadcn components needed by `08-UI-SPEC.md` under `frontend/src/components/ui/`, including `card`, `badge`, `input`, `tabs`, `separator`, and `skeleton`, plus any required Radix dependencies in `frontend/package.json` and `frontend/package-lock.json`. Create `frontend/src/components/trace/run-trace-summary-view.tsx` to render the compact run overview, step timeline preview, collection summary row, approved empty/error copy, and the primary CTA labels from the UI spec. Create `frontend/src/components/trace/run-trace-collection-panel.tsx` to render the active collection's controls and bounded results in one primary content column. Refactor `AgenticTraceView`, `DeepDiveLayout`, and `RunTraceJumpNav` so the existing dense `RunTraceExperience` and technical inspector remain available but visually subordinate below the summary-first surface. Add `frontend/src/components/trace/run-trace-summary-view.test.tsx` to cover overview-first reading order, separate collection labels, and the approved copy for empty/error states.</action>
  <acceptance_criteria>`frontend/src/components/trace/run-trace-summary-view.tsx` exists.
`frontend/src/components/trace/run-trace-collection-panel.tsx` exists.
`frontend/src/components/trace/run-trace-summary-view.tsx` contains `Inspect step details`.
`frontend/src/components/trace/run-trace-summary-view.tsx` contains `No trace details yet`.
`frontend/src/components/trace/run-trace-summary-view.tsx` contains `Trace details couldn't load`.
`frontend/src/components/trace/run-trace-summary-view.tsx` contains `Steps`, `Artifacts`, and `Model calls`.
`frontend/src/components/trace/agentic-trace-view.tsx` renders the summary-first surface before the technical inspector.
`frontend/src/components/trace/deep-dive-layout.tsx` still keeps the step timeline or section navigation visible as the organizing spine.
`frontend/src/components/trace/run-trace-summary-view.test.tsx` exists.
`cd frontend && npm run test -- run-trace-summary-view.test.tsx run-step-trace.test.tsx` passes once both tests exist.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- run-trace-summary-view.test.tsx run-step-trace.test.tsx</automated>
  </verify>
  <done>The trace page now opens as a restrained summary-first operator workflow with separate bounded collections and the timeline still acting as the main spine.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- run-trace-summary-view.test.tsx` after the typed route/page integration lands, then rerun `cd frontend && npm run test -- run-trace-summary-view.test.tsx run-step-trace.test.tsx` after the summary UI and collection panels are in place.
</verification>

<success_criteria>
Phase 08 satisfies the main UX part of `TRACE-01` and `TRACE-02` once the trace page opens on a compact overview plus timeline preview, uses URL-backed bounded collection navigation, and no longer depends on raw payload blobs for its first meaningful render.
</success_criteria>

<output>
After completion, create `.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-02-SUMMARY.md`
</output>
