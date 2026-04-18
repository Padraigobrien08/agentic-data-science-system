---
phase: 08-summary-first-large-trace-views
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/api/routes/runs.py
  - backend/schemas/api_phase_a.py
  - backend/repositories/run_step_repository.py
  - backend/repositories/model_call_repository.py
  - backend/repositories/artifact_repository.py
  - tests/test_trace_summary_api.py
  - tests/test_sprint3_transparency_api.py
autonomous: true
requirements:
  - TRACE-01
  - TRACE-02
  - TRACE-03
must_haves:
  truths:
    - "The trace page gains a typed first-load shell that returns run summary, timeline preview, and collection counts without raw run, step, or model-call payload blobs."
    - "Steps, artifacts, and model calls stay as separate bounded collections with server-side query parameters instead of one unbounded event stream."
    - "Privileged raw access moves to per-item step and model-call routes, while the existing slim transparency contract remains backward compatible."
  artifacts:
    - path: backend/api/routes/runs.py
      provides: "Typed trace-shell route, bounded collection queries, and item-scoped raw fetch endpoints"
    - path: backend/schemas/api_phase_a.py
      provides: "Trace-shell and collection response models that omit raw blobs by default"
    - path: tests/test_trace_summary_api.py
      provides: "Backend contract coverage for summary-first trace opening, bounded queries, and admin-gated raw item fetches"
    - path: tests/test_sprint3_transparency_api.py
      provides: "Compatibility coverage proving existing slim transparency responses still work after the new trace contract lands"
  key_links:
    - from: backend/api/routes/runs.py
      to: backend/schemas/api_phase_a.py
      via: "new trace-shell and collection endpoints serialize through typed slim models instead of raw JSON blobs"
      pattern: "trace-summary|RunTraceShellResponse|include_payloads=False"
    - from: backend/api/routes/runs.py
      to: backend/repositories/run_step_repository.py
      via: "bounded step queries and item lookup stay repository-backed instead of ad hoc route logic"
      pattern: "limit|offset|trace|step_id"
    - from: tests/test_trace_summary_api.py
      to: backend/api/routes/runs.py
      via: "tests lock summary-first omission of raw fields, collection query params, and per-item admin gating"
      pattern: "trace-summary|include_payloads|403"
---

<objective>
Add the backend contract for summary-first trace opening: one typed trace shell, bounded collection query parameters, and per-item raw fetch routes.

Purpose: satisfy the API-first part of `TRACE-01`, `TRACE-02`, and `TRACE-03` before the frontend trace page is rebuilt around the new contract.
Output: typed trace-shell response models, route/query support for steps or artifacts or model calls, and backend regressions proving raw payloads stay out of the first load.
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
@backend/api/routes/runs.py
@backend/schemas/api_phase_a.py
@backend/schemas/run_transparency.py
@backend/repositories/run_step_repository.py
@backend/repositories/model_call_repository.py
@backend/repositories/artifact_repository.py
@tests/test_api_phase_a.py
@tests/test_sprint3_transparency_api.py

<interfaces>
From `backend/api/routes/runs.py`:
```python
@router.get("/{run_id}", response_model=AnalysisRunDetailResponse)
def get_run(..., include_payloads: bool = Query(False), include_transparency: bool = Query(False))

@router.get("/{run_id}/steps", response_model=list[RunStepDetailItem])
def list_run_steps(..., include_payloads: bool = Query(False), include_transparency: bool = Query(False))

@router.get("/{run_id}/artifacts", response_model=list[ArtifactMetadata])
def list_run_artifacts(...)

@router.get("/{run_id}/model-calls", response_model=list[ModelCallApiItem])
def list_run_model_calls(..., include_payloads: bool = Query(False))
```

From `backend/schemas/api_phase_a.py`:
```python
class AnalysisRunDetailResponse(AnalysisRunSummary): ...
class RunStepDetailItem(RunStepListItem): ...
class ArtifactMetadata(BaseModel): ...
class ModelCallApiItem(BaseModel): ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add a typed trace-shell route that returns bounded previews without raw payload blobs</name>
  <files>backend/api/routes/runs.py
backend/schemas/api_phase_a.py
tests/test_trace_summary_api.py</files>
  <read_first>.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md
.planning/phases/08-summary-first-large-trace-views/08-RESEARCH.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
backend/api/routes/runs.py
backend/schemas/api_phase_a.py
backend/schemas/run_transparency.py
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - Per D-01 and D-02, the first trace load returns a compact run overview, timeline preview, and collection summaries without `output_payload_json`, `meta_json`, `planner_tool_input_json`, or model-call request/response blobs.
    - The trace shell must reuse the existing slim run and step converters plus typed transparency builders instead of inventing a second raw meta parsing layer.
    - Preview windows stay explicitly bounded by query params with safe defaults and capped maximums.
  </behavior>
  <action>Add new response models to `backend/schemas/api_phase_a.py` for a trace-opening contract such as `RunTraceCollectionSummary`, `RunTracePreviewWindow`, and `RunTraceShellResponse`. The shell must include the slim run summary, run-level transparency, a bounded `timeline_preview`, and separate preview/count sections for `steps`, `artifacts`, and `model_calls`. Then add `@router.get("/{run_id}/trace-summary", response_model=RunTraceShellResponse)` to `backend/api/routes/runs.py`. This route must require run ownership, must not expose an `include_payloads` query param, and must default to small preview limits like `5` or `10` with a capped maximum. Use `analysis_run_to_summary(...)`, `run_step_to_detail(... include_payloads=False, include_transparency=True)`, `artifact_to_metadata(...)`, and `model_call_to_api_item(... include_payloads=False)` so the shell never serializes raw payload JSON. Create `tests/test_trace_summary_api.py` with coverage that asserts the new route returns counts and preview rows while omitting raw run, step, and model-call payload fields by default.</action>
  <acceptance_criteria>`backend/api/routes/runs.py` contains `@router.get(\"/{run_id}/trace-summary\"`.
`backend/schemas/api_phase_a.py` contains `class RunTraceShellResponse`.
`backend/schemas/api_phase_a.py` contains `class RunTraceCollectionSummary`.
`backend/api/routes/runs.py` contains `steps_limit`.
`backend/api/routes/runs.py` contains `artifacts_limit`.
`backend/api/routes/runs.py` contains `model_calls_limit`.
`tests/test_trace_summary_api.py` exists.
`tests/test_trace_summary_api.py` contains `trace-summary`.
`tests/test_trace_summary_api.py` asserts raw run or step or model-call payload fields are omitted on the shell route.
`python3 -m pytest tests/test_trace_summary_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_trace_summary_api.py -q --tb=short</automated>
  </verify>
  <done>The backend now exposes one typed trace-opening response that is safe to use for large first loads.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add bounded collection query support and item-scoped raw fetch routes</name>
  <files>backend/api/routes/runs.py
backend/repositories/run_step_repository.py
backend/repositories/model_call_repository.py
backend/repositories/artifact_repository.py
tests/test_trace_summary_api.py
tests/test_sprint3_transparency_api.py</files>
  <read_first>.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md
.planning/phases/08-summary-first-large-trace-views/08-RESEARCH.md
.planning/phases/08-summary-first-large-trace-views/08-VALIDATION.md
backend/api/routes/runs.py
backend/repositories/run_step_repository.py
backend/repositories/model_call_repository.py
backend/repositories/artifact_repository.py
tests/test_trace_summary_api.py
tests/test_sprint3_transparency_api.py</read_first>
  <behavior>
    - Per D-03 and D-04, `steps`, `artifacts`, and `model-calls` remain separate navigable collections and each route gains bounded query parameters instead of returning one unfiltered list forever.
    - Per D-05 and D-06, privileged raw fetches are moved to one step or one model call at a time; list routes remain slim by default and no page-wide raw mode becomes the new default.
    - Existing Sprint 3 `include_transparency` semantics on `GET /v1/runs/{id}` and `GET /v1/runs/{id}/steps` must remain compatible.
  </behavior>
  <action>Extend the repositories with explicit bounded list helpers and item lookups suitable for route-level filtering: steps should support `limit`, `offset`, `status`, `trace`, and text `q`; artifacts should support `limit`, `offset`, `role_key`, `kind`, and `include_deleted`; model calls should support `limit`, `offset`, `status`, `prompt_id`, and text `q`. Update the existing list routes in `backend/api/routes/runs.py` to parse those query params, keep deterministic ordering, and return bounded rows. Add new item routes `GET /v1/runs/{run_id}/steps/{step_id}` and `GET /v1/runs/{run_id}/model-calls/{model_call_id}` that accept `include_payloads` and, for steps, `include_transparency`. These item routes must require run ownership, gate raw payloads with `require_admin_debug_access`, and return the same typed models as the list responses. Extend `tests/test_trace_summary_api.py` to cover filtering, pagination or offset behavior, and admin-only raw item fetches, then extend `tests/test_sprint3_transparency_api.py` so the older slim transparency flows still behave the same after the new query and item-route work lands.</action>
  <acceptance_criteria>`backend/api/routes/runs.py` contains `/{run_id}/steps/{step_id}`.
`backend/api/routes/runs.py` contains `/{run_id}/model-calls/{model_call_id}`.
`backend/api/routes/runs.py` contains `limit: int = Query(`.
`backend/api/routes/runs.py` contains `offset: int = Query(`.
`backend/api/routes/runs.py` contains `require_admin_debug_access(user, feature=\"raw run step payloads\")` or equivalent gating on the step item route.
`backend/api/routes/runs.py` contains `require_admin_debug_access(user, feature=\"raw model call payloads\")` or equivalent gating on the model-call item route.
`backend/repositories/run_step_repository.py` contains a bounded list helper beyond `list_for_analysis_run`.
`backend/repositories/model_call_repository.py` contains a bounded list helper beyond payload redaction candidates.
`backend/repositories/artifact_repository.py` contains a bounded list helper beyond `list_for_analysis_run`.
`tests/test_trace_summary_api.py` contains collection query coverage for `steps`, `artifacts`, and `model-calls`.
`tests/test_trace_summary_api.py` contains `403` coverage for non-admin raw item fetches.
`tests/test_sprint3_transparency_api.py` contains compatibility assertions for slim transparency responses after the new trace work.
`python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short</automated>
  </verify>
  <done>The backend now supports bounded trace navigation and per-item privileged raw access without breaking the existing slim transparency contract.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_trace_summary_api.py -q --tb=short` after the trace-shell route lands, then `python3 -m pytest tests/test_trace_summary_api.py tests/test_sprint3_transparency_api.py tests/test_run_transparency_builders.py -q --tb=short` after bounded queries and item routes are added.
</verification>

<success_criteria>
Phase 08 has a valid backend foundation once the trace page can open from one typed shell response, collection routes are bounded and queryable, and privileged raw step or model-call access is item-scoped rather than page-wide.
</success_criteria>

<output>
After completion, create `.planning/phases/08-summary-first-large-trace-views/08-summary-first-large-trace-views-01-SUMMARY.md`
</output>
