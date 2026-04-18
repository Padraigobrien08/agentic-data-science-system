# Phase 08: Summary-First Large Trace Views - Research

**Researched:** 2026-04-18
**Domain:** Summary-first large-run trace inspection without default raw-payload hydration
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Large traces should open on a compact overview with per-collection summaries instead of the current full deep-dive stack.
- **D-02:** Heavier detail sections should open only through drill-down so the first load stays bounded.
- **D-03:** Steps, artifacts, and model calls remain separate navigable collections rather than one mixed event stream.
- **D-04:** Each collection needs its own bounded navigation controls instead of relying only on page anchors.
- **D-05:** Privileged raw payloads must be fetched on demand for one item at a time rather than page-wide.
- **D-06:** The on-demand raw view should stay local to the selected item or pane, not restore `include_payloads=true` as the default page shape.
- **D-07:** The step timeline remains the primary spine for understanding the run.
- **D-08:** Artifacts and model calls should link back to the step spine through phase, role, status, and linked-item cues.

### the agent's Discretion
- Exact summary endpoint shape, as long as the first load is typed and bounded
- Exact query parameters and pagination style for steps, artifacts, and model calls
- Exact breakpoint or heuristic for when the UI emphasizes “large run” controls
- Exact drawer, inline, or side-panel treatment for raw item expansion

### Deferred Ideas (OUT OF SCOPE)
- Cross-run evidence coverage or weak-evidence analytics
- A dedicated evaluation operator control plane
- Direct bucket browsing, presigned URLs, or other storage-surface changes
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TRACE-01 | User can open large run trace views that load typed summaries first without default full-payload hydration | Move the opening load to a dedicated typed trace shell or equivalent summary contract that does not require `output_payload_json`, `meta_json`, or full step payloads. |
| TRACE-02 | User can search, filter, paginate, or jump through large step, artifact, and model-call collections without overwhelming the browser or API | Add collection-specific query contracts and URL-backed navigation instead of in-memory full-list rendering. |
| TRACE-03 | Privileged users can fetch raw payload sections on demand in bounded views instead of receiving all raw trace blobs by default | Replace page-wide `include_payloads=true` behavior with item-scoped raw fetch paths guarded by existing admin-debug access. |
</phase_requirements>

## Summary

The current trace route is still optimized for small runs. `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` does a first-render `Promise.all` over `getRun(... includePayloads: true)`, `listRunSteps(... includePayloads: true)`, `listRunArtifacts()`, and `listRunModelCalls(...)`, then hands raw `output_payload_json` and `meta_json` to `AgenticTraceView`. That means the default trace experience still depends on the largest blobs in the system, and the frontend is responsible for parsing those blobs into most of the page structure.

The repo already has the right seams to fix this incrementally. `backend/schemas/run_transparency.py` and `backend/schemas/api_phase_a.py` already separate slim typed views from raw payload inclusion. The frontend also already distinguishes a narrative audit surface (`RunTraceExperience`) from a lower-level inspector (`RunStepTrace`, `ModelCallSummaryCard`, artifact detail routes). Phase 8 should build on those seams by pushing more of the “first open” summary into typed backend responses, not by adding a client-heavy caching layer or collapsing the trace into one giant virtualized list.

The lowest-risk design is a three-part shape. First, add a dedicated typed trace-shell response, or equivalent coordinated summary contract, that gives the page enough run, timeline, transparency, and collection-count data to render an overview without raw JSON. Second, add bounded collection queries for steps, artifacts, and model calls with URL-backed search or filter or pagination state so navigation can stay server-driven and inspectable. Third, move privileged raw access to item-scoped fetches: one step, one model call, or one artifact metadata view at a time. That keeps brownfield semantics intact while removing the current “all raw on first open” bottleneck.

**Primary recommendation:** keep the page architecture SSR-first and query-param-driven. Use the Next App Router page to render a typed overview and bounded collection results from the server, then use small client islands only for local item expansion or interaction polish. That preserves existing auth and data-access patterns, keeps large traces shareable through URLs, and avoids introducing a second data layer just to solve a response-shape problem.

Repo note: `AGENTS.md` was applied. No repository-local `.claude/skills/` or `.agents/skills/` directory exists under the project root.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| Existing FastAPI run routes and Pydantic response models | in-repo seam | Add typed trace-shell and collection query contracts | The repo already exposes slim vs raw models and ownership or admin gating in `backend/api/routes/runs.py` and `backend/schemas/api_phase_a.py`. |
| Existing Next.js App Router server-rendered page flow | Next.js 15 / React 19 | Drive summary-first trace rendering from URL state | The current trace page is already server rendered, so bounded query-state navigation fits the existing architecture without new client data infra. |
| Existing `RunTransparencySummary` and `RunStepTransparencyView` | in-repo seam | Reuse typed summaries instead of re-parsing raw JSON in the browser | These schemas already capture evidence IDs, prompt versions, per-step summaries, and linked artifact IDs. |
| `pytest 8.4.2` and `vitest run` | local repo tooling | Backend contract and frontend rendering regressions | Existing transparency and trace work already relies on these suites. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `frontend/src/lib/api/runs.ts` + `frontend/src/lib/api/types.ts` | in-repo seam | Introduce typed trace summary and paged collection fetch helpers | Use when converting the route away from raw first-load payloads. |
| `frontend/src/components/trace/deep-dive-layout.tsx` + `run-trace-jump-nav.tsx` | in-repo seam | Host the lighter overview and collection-level jump behavior | Use for the top-level structure rather than replacing the whole trace page. |
| Existing artifact detail route and panel | in-repo seam | Preserve artifact drill-down behavior without inventing new storage exposure | Use for collection-to-detail linking and bounded previews. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Dedicated typed trace shell plus bounded collection queries | Keep the current `getRun(... includePayloads: true)` + full lists on first render | Simpler short-term, but it preserves the exact scale problem this phase exists to solve. |
| URL-backed server-rendered search, filter, and pagination | Add TanStack Query or a browser-side state cache for full collections | More dynamic, but it adds a new data layer without fixing the oversized API contract first. |
| Separate steps, artifacts, and model calls collections | Collapse everything into a unified event stream | Easier to scroll, but it weakens the distinct semantics the user already approved and makes filtering harder to reason about. |
| Item-scoped raw fetches | Page-wide admin reloads with `include_payloads=true` | Reuses existing route params, but it keeps privileged payload volume unbounded and couples one detail action to the whole page. |
| Reuse typed backend summaries | Parse raw `output_payload_json` and `meta_json` in more frontend helpers | Lowest engineering friction, but it keeps large transport blobs and browser work where the phase is trying to remove them. |

## Architecture Patterns

### Pattern 1: Typed Trace Shell for the First Paint

**What:** Add one trace-opening contract that returns bounded run overview data, summary counters for collections, timeline summary rows, and existing transparency slices without including raw run or step payload blobs.

**When to use:** Every initial load of `/projects/[projectId]/runs/[runId]/trace`.

**Why:** The page currently depends on raw `output_payload_json` and `meta_json` just to render its first meaningful view. Moving the first paint to typed data is the central requirement of this phase.

**Recommended contract elements:**
- run summary and status
- collection counts for steps, artifacts, and model calls
- compact timeline preview rows using `RunStepTransparencyView`
- run-level transparency summary and optional pre-derived overview sections
- small preview windows for each collection, not full lists

### Pattern 2: Query-Backed Collection Endpoints

**What:** Keep steps, artifacts, and model calls as separate endpoints or subresources, but add bounded query parameters such as `limit`, `cursor` or `offset`, filter fields, and simple search terms.

**When to use:** Any collection list rendered under the trace view.

**Why:** `TRACE-02` is about navigation scale, not just visual layout. The current endpoints return full lists and leave the browser to cope.

**Recommended behavior:**
- Steps: filter by status, lane or trace, and free-text label/detail search
- Artifacts: filter by role, kind, or deletion state
- Model calls: filter by status, prompt id or version, and phase or provider cues
- Keep URLs shareable and SSR-friendly by using search params as the source of truth

### Pattern 3: Timeline Spine, Collections as Linked Lenses

**What:** Treat the step timeline as the canonical execution spine, then let artifacts and model calls reference it through linked IDs, phase labels, run-step IDs, and status chips.

**When to use:** In the overview and when drilling into collection rows.

**Why:** The user explicitly approved keeping separate collections while still anchoring the experience in the run timeline.

**Recommended UI behavior:**
- Overview starts with a compact timeline summary
- Artifact and model-call rows show the nearest step or phase cue
- Jump actions land back on the relevant timeline or collection state, not only on top-level page anchors

### Pattern 4: Item-Scoped Raw Expansion

**What:** Raw run-step meta, planner input, model request/response payloads, and artifact metadata or preview bodies are fetched only when a privileged user opens a specific item.

**When to use:** Debug or audit drill-down by an admin user.

**Why:** Existing routes already understand admin-only raw access, but the current list endpoints fetch raw payloads in bulk.

**Recommended contract:**
- add single-item detail fetches for steps and model calls, or equivalent item-scoped raw routes
- keep artifact detail and preview on the existing artifact routes
- only fetch raw JSON for the selected row; never mutate the whole page into a raw mode

### Pattern 5: SSR-First, Client Islands Second

**What:** Keep first-load data access in server components and use small client components only for local collection controls, drawer state, or per-item raw expansion UX.

**When to use:** The overall Phase 8 page architecture.

**Why:** The repo architecture already prefers server-side data fetching and typed view models. Phase 8 does not need a frontend data-platform rewrite.

**Recommended behavior:**
- overview and collection queries render on the server from URL search params
- client islands handle drawer open state, inline expansion state, and maybe debounced filter inputs
- no browser-side direct FastAPI access; keep existing auth and server-only fetch patterns

## Implementation Slices

### Slice A: Backend Trace Shell and Collection Query Contract

Focus files:
- `backend/api/routes/runs.py`
- `backend/schemas/api_phase_a.py`
- `backend/schemas/run_transparency.py`
- `tests/test_trace_summary_api.py`
- `tests/test_sprint3_transparency_api.py`

Deliver:
- a bounded trace-opening summary contract
- paged or filtered collection query support
- item-scoped raw fetch paths for steps and model calls
- backward-compatible raw gating that keeps admin debug access explicit

### Slice B: Frontend Summary-First Trace Experience

Focus files:
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/components/trace/agentic-trace-view.tsx`
- `frontend/src/components/trace/run-trace-experience.tsx`
- `frontend/src/components/trace/deep-dive-layout.tsx`

Deliver:
- typed overview-first trace page
- separate bounded collections for steps, artifacts, and model calls
- URL-backed navigation, search, filter, or pagination state
- reduced dependence on raw `output_payload_json` and `meta_json` for default render

### Slice C: Per-Item Raw Expansion and Regression Coverage

Focus files:
- `frontend/src/components/runs/run-step-trace.tsx`
- `frontend/src/components/transparency/model-call-summary-card.tsx`
- `frontend/src/components/trace/artifact-detail-panel.tsx`
- `frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx`
- `frontend/src/components/runs/run-step-trace.test.tsx`
- `docs/artifact-delivery.md`

Deliver:
- raw expansion only when a privileged user opens one item
- bounded detail panes or drawers for step and model-call JSON
- artifact detail linkage that stays app-owned and opaque
- UI and API regressions proving first load stays summary-first

## Validation Architecture

Phase 08 should introduce one new backend contract test file and one or two targeted frontend rendering or interaction test files, while extending the existing Sprint 3 transparency coverage rather than replacing it.

**Recommended quick command:**
```bash
python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short && cd frontend && npm run test -- run-trace-summary-view.test.tsx model-call-summary-card.test.tsx run-step-trace.test.tsx
```

**Recommended full command:**
```bash
python3 -m pytest tests/ -q --tb=short && cd frontend && npm run test
```

**Required new or expanded tests:**
- `tests/test_trace_summary_api.py`
  - typed trace-shell response excludes raw payloads by default
  - steps or artifacts or model-calls collection queries support bounded filters and pagination
  - item-scoped raw endpoints enforce admin debug access
- `tests/test_sprint3_transparency_api.py`
  - backward-compatible transparency behavior still works for slim responses
  - existing `include_transparency` semantics survive the new summary-first trace contract
- `frontend/src/components/trace/run-trace-summary-view.test.tsx`
  - overview-first render shows collection summaries before raw sections
  - separate collections stay distinct and timeline remains visible
- `frontend/src/components/runs/run-step-trace.test.tsx`
  - raw step JSON stays hidden until explicit expansion
- `frontend/src/components/transparency/__tests__/model-call-summary-card.test.tsx`
  - payload sections stay omitted by default and render only when raw data is present from a bounded fetch

## Pitfalls and Boundaries

- Do not keep the current first-load dependency on `include_payloads=true` for runs or steps.
- Do not move large-run navigation entirely into client-side in-memory filtering of full collections.
- Do not collapse steps, artifacts, and model calls into one mixed stream just to simplify rendering.
- Do not reintroduce page-wide raw payload toggles as the primary privileged workflow.
- Do not let the frontend depend on storage locators or other artifact-delivery implementation details.
- Do not remove the existing dense technical inspector entirely; it should become drill-down, not disappear.

## Recommended Plan Shape

Phase 08 should be planned as **3 sequential plans**:

1. **Backend summary contract** — add the typed trace shell, collection query parameters, and item-scoped raw endpoints
2. **Frontend summary-first view** — rebuild the trace route around overview-first SSR and bounded collection navigation
3. **Raw drill-down and regressions** — wire per-item raw expansion, preserve inspector usefulness, and harden backend plus frontend tests

This sequence keeps the API contract first, the main experience second, and the privileged drill-down plus hardening work last. It also matches the repo’s architecture preference: typed backend surfaces first, UI composition second.

## Sources

### Primary
- `.planning/PROJECT.md`
- `.planning/REQUIREMENTS.md`
- `.planning/ROADMAP.md`
- `.planning/STATE.md`
- `.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md`
- `backend/api/routes/runs.py`
- `backend/schemas/api_phase_a.py`
- `backend/schemas/run_transparency.py`
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/components/trace/agentic-trace-view.tsx`
- `frontend/src/components/trace/run-trace-experience.tsx`
- `frontend/src/components/trace/deep-dive-layout.tsx`
- `frontend/src/components/trace/run-trace-jump-nav.tsx`
- `frontend/src/components/transparency/model-call-summary-card.tsx`
- `frontend/src/components/runs/run-step-trace.tsx`
- `frontend/src/app/artifacts/[artifactId]/page.tsx`
- `frontend/src/components/trace/artifact-detail-panel.tsx`
- `tests/test_sprint3_transparency_api.py`
- `tests/test_run_transparency_builders.py`

