---
phase: 13-analyst-prompt-routing
plan: 02
type: execute
wave: 2
depends_on:
  - 01
files_modified:
  - edgar_project/orchestration/schemas.py
  - edgar_project/orchestration/planner.py
  - backend/schemas/prompt_routing.py
  - backend/api/routes/runs.py
  - tests/orchestration/test_planner.py
  - tests/test_prompt_routing_api.py
autonomous: true
requirements:
  - PROMPT-03
must_haves:
  truths:
    - "Unsupported routing returns concrete rewrite suggestions and scope guidance instead of only `supported intent ids`."
    - "Chat can preview routing deterministically before run creation through an additive backend contract."
    - "The new routing contract makes the trust boundary explicit by reporting `routing_source` as deterministic in Phase 13."
  artifacts:
    - path: backend/schemas/prompt_routing.py
      provides: "Typed request/response contract for deterministic route previews and rewrite suggestions"
    - path: backend/api/routes/runs.py
      provides: "Additive `POST /v1/runs/route-preview` endpoint that previews routing without creating a run"
    - path: tests/test_prompt_routing_api.py
      provides: "API regression coverage for supported previews, unsupported guidance, and project ownership"
  key_links:
    - from: backend/api/routes/runs.py
      to: edgar_project/orchestration/planner.py
      via: "Route preview uses the same deterministic planner as execution, so preview and execution cannot drift semantically"
      pattern: "Planner|route-preview|rewrite_suggestions"
    - from: edgar_project/orchestration/schemas.py
      to: backend/schemas/prompt_routing.py
      via: "Planner guidance fields are surfaced through a typed backend response contract"
      pattern: "rewrite_suggestions|routing_source|effective_tickers"
    - from: tests/test_prompt_routing_api.py
      to: backend/api/routes/runs.py
      via: "Ownership and unsupported-guidance behavior are locked at the HTTP boundary"
      pattern: "supported=false|routing_source"
---

<objective>
Add a deterministic preview and guidance contract so unsupported prompts return actionable rewrite suggestions before chat creates a failed run.

Purpose: satisfy `PROMPT-03` at the backend boundary and make the deterministic trust source explicit.
Output: structured planner guidance, additive preview endpoint, and API regression coverage.
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
@.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
@.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
@.planning/phases/13-analyst-prompt-routing/13-VALIDATION.md
@edgar_project/orchestration/schemas.py
@edgar_project/orchestration/planner.py
@backend/api/routes/runs.py
@backend/schemas/execute_run.py
@tests/orchestration/test_planner.py
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Make unsupported planner failures carry concrete rewrite guidance and explicit routing provenance</name>
  <files>edgar_project/orchestration/schemas.py
edgar_project/orchestration/planner.py
tests/orchestration/test_planner.py</files>
  <read_first>.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
edgar_project/orchestration/schemas.py
edgar_project/orchestration/planner.py
tests/orchestration/test_planner.py</read_first>
  <behavior>
    - Deterministic unsupported routing must return machine-readable rewrite suggestions and routing provenance, not only a generic detail string.
    - Guidance must reflect prompt-scope failures such as out-of-scope ticker mentions.
    - The Phase 13 path must remain explicitly deterministic; it must not invoke model-assisted rescue.
  </behavior>
  <action>Extend the orchestration-layer schemas so unsupported planning failures can carry `rewrite_suggestions`, `effective_tickers`, `out_of_scope_tickers`, and `routing_source`. Keep `routing_source` a required field for this new guidance surface and set it to the exact string `deterministic` in Phase 13. In `edgar_project/orchestration/planner.py`, replace the current `_unsupported_goal_failure()` implementation with a guidance builder that returns 2-3 concrete rewrite suggestions based on the failed prompt shape. Include a scope-specific suggestion whenever `out_of_scope_tickers` is non-empty. Keep this guidance deterministic and do not call `maybe_apply_llm_intent_preferences(...)` or any model-backed helper. Extend `tests/orchestration/test_planner.py` so unsupported outputs assert `rewrite_suggestions` exists, `routing_source == "deterministic"`, and out-of-scope symbol prompts include the missing ticker in the response.</action>
  <acceptance_criteria>`edgar_project/orchestration/schemas.py` contains `rewrite_suggestions`.
`edgar_project/orchestration/schemas.py` contains `routing_source`.
`edgar_project/orchestration/planner.py` contains `routing_source=\"deterministic\"` or `routing_source = \"deterministic\"`.
`edgar_project/orchestration/planner.py` contains `rewrite_suggestions`.
`tests/orchestration/test_planner.py` contains `rewrite_suggestions`.
`tests/orchestration/test_planner.py` contains `routing_source`.
`tests/orchestration/test_planner.py` contains `TSLA` or another out-of-scope ticker assertion.
`edgar_project/orchestration/planner.py` does not contain `maybe_apply_llm_intent_preferences`.
`python3 -m pytest tests/orchestration/test_planner.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/orchestration/test_planner.py -q --tb=short</automated>
  </verify>
  <done>Unsupported deterministic planning now produces structured guidance that later callers can preview and render directly.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add an additive deterministic route-preview API without changing run creation semantics</name>
  <files>backend/schemas/prompt_routing.py
backend/api/routes/runs.py
tests/test_prompt_routing_api.py</files>
  <read_first>.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
backend/api/routes/runs.py
backend/schemas/execute_run.py
backend/schemas/analysis_run.py
tests/test_auth_api.py
tests/test_secure_defaults_api.py</read_first>
  <behavior>
    - Chat and other callers must be able to preview routing before creating a run.
    - Preview must be project-scoped and ownership-checked.
    - Existing `POST /v1/runs` and `POST /v1/runs/{run_id}/execute` semantics must remain unchanged.
  </behavior>
  <action>Add a new schema module `backend/schemas/prompt_routing.py` with `PromptRoutingPreviewRequest` and `PromptRoutingPreviewResponse`. The request should accept `project_id`, `analysis_goal`, `tickers`, and optional `refresh`. The response should include `supported`, `routing_source`, `effective_tickers`, `out_of_scope_tickers`, `rewrite_suggestions`, `reason`, and when supported also `intent`, `goal_code`, and `plan_template_id`. In `backend/api/routes/runs.py`, add `@router.post(\"/route-preview\")` that requires project ownership with `require_project_owned(...)`, constructs `OrchestrationInput` from the request payload, calls the deterministic `Planner`, and returns the typed preview response without creating an `AnalysisRun`. Preserve all existing create and execute endpoints exactly as they are. Add `tests/test_prompt_routing_api.py` covering a supported preview that narrows to `MSFT`, an unsupported preview that names out-of-scope `TSLA` and returns `rewrite_suggestions`, and a not-owned project case that returns the existing ownership failure behavior.</action>
  <acceptance_criteria>`backend/schemas/prompt_routing.py` exists.
`backend/schemas/prompt_routing.py` contains `PromptRoutingPreviewRequest`.
`backend/schemas/prompt_routing.py` contains `PromptRoutingPreviewResponse`.
`backend/api/routes/runs.py` contains `@router.post("/route-preview")`.
`backend/api/routes/runs.py` contains `require_project_owned`.
`backend/api/routes/runs.py` contains `Planner()`.
`tests/test_prompt_routing_api.py` exists.
`tests/test_prompt_routing_api.py` contains `route-preview`.
`tests/test_prompt_routing_api.py` contains `routing_source`.
`tests/test_prompt_routing_api.py` contains `rewrite_suggestions`.
`python3 -m pytest tests/test_prompt_routing_api.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_prompt_routing_api.py -q --tb=short</automated>
  </verify>
  <done>The backend exposes a deterministic preview contract that unsupported chat requests can use before any run row is created.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/orchestration/test_planner.py tests/test_prompt_routing_api.py -q --tb=short` after both tasks land.
</verification>

<success_criteria>
Phase 13 has a safe backend contract once unsupported routing can be previewed deterministically, with rewrite suggestions and scope guidance returned before run creation.
</success_criteria>

<output>
After completion, create `.planning/phases/13-analyst-prompt-routing/13-analyst-prompt-routing-02-SUMMARY.md`
</output>
