# Phase 8: Summary-First Large Trace Views - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Make large run traces usable without default full-payload hydration by moving the first load to typed summaries, adding bounded navigation over large step/artifact/model-call collections, and keeping privileged raw payload inspection explicit and on-demand.

This phase covers the default trace-opening shape, collection-level navigation, raw expansion behavior, and the ordering/linking model that ties evidence back to the run timeline. It does not add a new evaluation control plane, cross-run analytics, or bucket-direct artifact browsing.

</domain>

<decisions>
## Implementation Decisions

### Opening trace shape
- **D-01:** The default trace experience should open on a compact overview with per-collection summary panels first, not the current all-sections deep-dive stack.
- **D-02:** Heavier sections should open only through drill-down from those summary panels so the first load stays bounded on very large runs.

### Collection navigation model
- **D-03:** Steps, artifacts, and model calls should remain separate collections rather than being collapsed into one mixed event stream.
- **D-04:** Each collection should get its own bounded navigation controls such as search, filtering, pagination, or jump behavior instead of relying only on page anchors.

### Raw expansion pattern
- **D-05:** Privileged raw payloads should be fetched on demand for one item at a time instead of loading page-wide raw run/step/model payloads up front.
- **D-06:** The on-demand raw view should expand inline or in a local detail pane/drawer attached to the current item, not through a global `include_payloads=true` first load.

### Default ordering and evidence linking
- **D-07:** The step timeline remains the primary spine for understanding a run.
- **D-08:** Artifacts and model calls should pin back to that spine using phase, role, status, and linked-item cues instead of reordering everything newest-first.

### the agent's Discretion
- Exact API shape for summary-first trace responses, as long as the first load stays bounded and typed
- Exact threshold or heuristics for when the UI switches from “small run” behavior to explicit large-run controls
- Exact filter chips, search semantics, and pagination style for each collection
- Exact inline detail treatment for raw expansions, as long as it is per-item and on-demand

</decisions>

<specifics>
## Specific Ideas

- User accepted all recommended defaults in one pass:
  - compact overview plus per-collection summaries first
  - separate collections for steps, artifacts, and model calls
  - privileged raw payloads fetched on demand per item
  - step timeline remains the organizing spine for evidence
- Existing dense audit content is still valuable, but it should become a drill-down layer rather than the default opening state for large runs.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — current milestone intent, brownfield constraints, and the API-first summary-first direction already locked for v1.1
- `.planning/REQUIREMENTS.md` — `TRACE-01`, `TRACE-02`, and `TRACE-03` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 8 goal, dependencies, and success criteria
- `.planning/STATE.md` — current project position after Phase 7 completion

### Prior phase decisions that constrain this phase
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — raw run/model payload access must remain privileged and summary-first by default
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md` — artifact delivery and retention-visible states must stay truthful as trace views become more bounded
- `.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md` — artifact identity and delivery remain app-owned and opaque even when backing storage is remote

### Current backend trace and payload surfaces
- `backend/api/routes/runs.py` — current run, step, and model-call fetch contract; today `/trace` still depends on `include_payloads=true`
- `backend/schemas/api_phase_a.py` — slim-vs-raw response models and per-resource payload gating
- `backend/schemas/run_transparency.py` — existing typed run/step transparency summaries that Phase 8 should expand instead of bypassing
- `backend/schemas/llm_usage.py` — existing per-run LLM usage rollups already exposed as bounded transparency data

### Current frontend trace and evidence surfaces
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` — current trace page fetch pattern and initial load behavior
- `frontend/src/lib/api/runs.ts` — server-side fetch wrappers that will need new summary-first query shapes or endpoints
- `frontend/src/lib/api/types.ts` — typed wire models for run, step, artifact, model-call, and transparency slices
- `frontend/src/components/trace/agentic-trace-view.tsx` — current trace composition boundary between audit narrative and technical inspector
- `frontend/src/components/trace/run-trace-experience.tsx` — current all-sections audit body and evidence/timeline/model-call ordering
- `frontend/src/components/trace/deep-dive-layout.tsx` — existing summary shell and jump-nav layout seam
- `frontend/src/components/trace/run-trace-jump-nav.tsx` — current section navigation pattern that large-run collection nav must either extend or replace
- `frontend/src/components/transparency/model-call-summary-card.tsx` — current per-item model-call summary plus optional raw JSON details
- `frontend/src/components/runs/run-step-trace.tsx` — current persisted-step raw inspector that loads full step meta eagerly
- `frontend/src/app/artifacts/[artifactId]/page.tsx` — existing separate artifact detail route that can inform per-item drill-down behavior
- `frontend/src/components/trace/artifact-detail-panel.tsx` — current evidence-detail pattern with preview/download separated from metadata

### Delivery constraints
- `docs/artifact-delivery.md` — artifact detail and preview/download behavior must remain app-owned and opaque while trace linking becomes more granular

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/schemas/run_transparency.py` — already provides typed, bounded run-level and step-level transparency slices that can become the summary-first API foundation
- `backend/schemas/api_phase_a.py` — already separates slim responses from raw payload expansions via `include_payloads`
- `frontend/src/components/trace/deep-dive-layout.tsx` and `frontend/src/components/trace/run-trace-jump-nav.tsx` — existing sectioned shell and navigation that can host a lighter overview layer
- `frontend/src/components/transparency/model-call-summary-card.tsx` — existing per-item summary-plus-details card pattern for model calls
- `frontend/src/app/artifacts/[artifactId]/page.tsx` and `frontend/src/components/trace/artifact-detail-panel.tsx` — existing separate detail route/panel pattern for artifacts

### Established Patterns
- The current `/trace` page is server-rendered and fetches `getRun(... includePayloads: true)` plus full step payloads up front; this is the main large-run pressure point
- Raw payload access is already admin-gated in the backend and omitted from default API responses, so Phase 8 should extend that pattern instead of introducing a new trust model
- The UI already distinguishes the dense audit narrative from the lower-level technical inspector, which makes a summary-first opening state additive rather than a total redesign
- Artifacts, steps, and model calls already exist as distinct backend collections with typed summaries, which supports separate navigation models naturally

### Integration Points
- `backend/api/routes/runs.py` and `backend/schemas/*` — summary-first run/step/model-call contracts, query params, and new bounded collection responses
- `frontend/src/lib/api/runs.ts` and `frontend/src/lib/api/types.ts` — adapting server fetches and wire models away from initial full-payload loads
- `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` — changing the first-load data bundle for the trace route
- `frontend/src/components/trace/*` and `frontend/src/components/transparency/*` — building the lighter overview, collection navigation, and per-item drill-down paths

</code_context>

<deferred>
## Deferred Ideas

- Cross-run evidence-coverage and weak-evidence summaries — already deferred to `TRACE-04`
- Evaluation-run operator workflows and dedicated evaluation UI — Phase 9 and later
- Signed/direct artifact delivery paths — already out of scope from Phase 7

</deferred>

---

*Phase: 08-summary-first-large-trace-views*
*Context gathered: 2026-04-18*
