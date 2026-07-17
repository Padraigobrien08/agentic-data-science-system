# Current System Architecture (Brownfield Audit)

Status: **audit only — no target code implemented here.** This document maps the
system as it exists today (EDGAR-specific financial analysis platform), so the
generalization to an input-agnostic agentic data-science platform can be staged
against a known baseline.

Companion docs: [`target-system.md`](./target-system.md),
[`migration-plan.md`](./migration-plan.md),
[`domain-boundaries.md`](./domain-boundaries.md).

---

## 1. Current-system architecture map

Seven cooperating layers (top → bottom is request → computation):

```
┌──────────────────────────────────────────────────────────────────────┐
│ 1. Frontend (Next.js App Router)          frontend/src/app, components │
│    chat-first shell → server actions → server-side API client          │
├──────────────────────────────────────────────────────────────────────┤
│ 2. Server-side API access (Next.js)       frontend/src/lib/api,        │
│    JWT stays server-side; artifact proxy   frontend/src/actions         │
├──────────────────────────────────────────────────────────────────────┤
│ 3. FastAPI HTTP API + auth + ownership    backend/api/*                │
│    /health /metrics /v1/{auth,projects,runs,artifacts,evaluations}     │
├──────────────────────────────────────────────────────────────────────┤
│ 4. Services / repositories / models       backend/services, repositories,│
│    lifecycle, queue, artifacts, persistence  models, schemas, db        │
├──────────────────────────────────────────────────────────────────────┤
│ 5. Traceable agent pipeline               backend/agents/*             │
│    MCP-trace persistence + critic LLM + report LLM                     │
├──────────────────────────────────────────────────────────────────────┤
│ 6. Orchestration (plan → execute)         edgar_project/orchestration  │
│    deterministic Planner + Executor over MCP tools                     │
├──────────────────────────────────────────────────────────────────────┤
│ 7a. MCP tool layer   edgar_project/mcp    7b. Deterministic compute src/ │
│     schemas/adapters/tools/server              data_fetch → report      │
└──────────────────────────────────────────────────────────────────────┘
        Cross-cutting: backend/storage (artifacts), backend/observability
        Background:    backend/worker (DB-queue poller → layer 5)
        Offline eval:  edgar_project/evaluation (fixtures + regression)
```

Entry points (`grep`-confirmed):

- `backend/main.py:create_app` — ASGI app; mounts `ObservabilityMiddleware`,
  `/health`, `/metrics`, `/v1/*`.
- `backend/worker/__main__.py` → `backend/worker/loop.py:run_forever` — queue poller.
- `frontend/src/app/layout.tsx` — web shell.
- `edgar_project/cli.py` — `run`, `demo`, `demo --fixtures`, `evaluate`.
- `edgar_project/mcp/server.py` — stdio MCP server.
- `main.py` — repo-root Phase-1 pipeline (no backend shell).

---

## 2. Exact execution path: user prompt → persisted report

Traced from `frontend/src/actions/runs.ts:createAnalysisRunFromChat` down to
`backend/services/edgar_pipeline_execution_service.py`.

1. **Chat submit (browser).** Chat form posts `goal`, `tickers`, `refresh` to the
   server action `createAnalysisRunFromChat` (`frontend/src/actions/runs.ts:43`).
2. **Route preview (deterministic gate).** Action calls `POST /v1/runs/route-preview`
   → `backend/api/routes/runs.py:route_preview` → `Planner().build_plan(...)`.
   If `supported=false`, the action returns rewrite suggestions and **no run is
   created** (`runs.ts:76`).
3. **Create run.** `POST /v1/runs` → `runs.py:create_run` →
   `AnalysisRunService.create(...)` inserts an `analysis_runs` row in status
   `pending` with `input_payload_json = {tickers, analysis_goal, refresh}`.
   Chat uses `enqueue_execution=false` (synchronous path). Project ownership is
   enforced first (`require_project_owned`).
4. **Execute (synchronous).** `POST /v1/runs/{id}/execute` → `runs.py:execute_run`
   → `EdgarPipelineExecutionService.execute_analysis_run(run_id, ...)`.
   - Guards status (must be in `_EXECUTABLE_STATUSES`), builds `OrchestrationInput`.
   - Optionally applies **LLM intent preferences** (`maybe_apply_llm_intent_preferences`)
     — refines `GoalPreferences` only; never selects tools.
   - Transitions run → `running`, builds a run-scoped `RunWorkspace`, records it in
     `meta_json.run_workspace`.
   - Calls `run_traceable_edgar_pipeline(session, run_id, orch_in, ...)`.
5. **Traceable pipeline** (`backend/agents/traceable_analysis_pipeline.py`), a
   **fixed linear chain**:
   1. `coordinator(orch_in)` = `AnalysisAgent.run_returning_state` →
      `Planner.build_plan` (deterministic template selection) →
      `Executor.run_returning_state` (runs MCP tools in plan order).
   2. `persist_orchestration_step_trace(...)` writes one `RunStep` per planned step
      and one `ToolCall` + envelope per executed MCP step.
   3. Writes `meta_json.ai_agents.{intent,planning,prompt_versions}`.
   4. **Critic (LLM)** — `CriticAgent` over artifact excerpts + orchestration
      summary; recorded as a `ModelCall` and a `RunStep`.
   5. **Report (LLM)** — `ReportAgent`, gated on critic success; produces
      `output_payload_json.user_facing_report`.
6. **MCP tools compute** (`edgar_project/orchestration/executor.py:_dispatch_mcp`
   → `edgar_project/mcp/tools.py` → `edgar_project/mcp/adapters.py` → `src/*`).
   The deterministic pipeline (`resolve_company → fetch → build_panel →
   compute_features → detect_anomalies → generate_report`, or a single
   `run_pipeline`) writes CSV/Markdown into the run workspace.
7. **Persist outcome** (back in the execution service): `set_output_payload`
   (full `OrchestrationOutput`), `merge_output_payload` (report patch), map
   orchestration status → `AnalysisRunStatus`, **ingest each artifact file** via
   `ArtifactService.ingest_pipeline_file` into the object store (rows in
   `artifacts` with `storage_uri`), `enrich_traceability_artifact_ids`, transition
   to terminal status, `commit`.
8. **Read back (browser).** Action calls `GET /v1/runs/{id}?include_transparency=1`
   and `GET /v1/runs/{id}/artifacts`, parses `output_payload_json` /
   `meta_json.ai_agents` into a chat answer card. Artifact bytes stream later via
   `GET /v1/artifacts/{id}/content` (proxied through Next.js).

Background variant: `enqueue_execution=true` (or `POST /v1/runs/{id}/retry`) makes
`RunQueueService` insert a `run_execution_jobs` row (status `queued`). The worker
(`loop.py:process_next_job`) claims it with a lease + fencing `claim_token`, runs
the **same** `EdgarPipelineExecutionService` with `from_worker=True`, then
finalizes (complete / requeue-transient / cancel / fail) with attempt history.

---

## 3. Dependency map

Arrows = "depends on / calls". No cycles across layer boundaries.

```
frontend ──▶ API (HTTP /v1) ──▶ services ──▶ repositories ──▶ models ──▶ db(Postgres/SQLite)
   │                                │                                     ▲
   └── artifact proxy ──▶ API ──────┘                                     │
                                    │                                     │
API ──▶ services.EdgarPipelineExecutionService ──▶ agents.traceable_pipeline
                                    │                        │
worker ──▶ (same execution service)│                        ├──▶ agents.critic/report ──▶ llm.factory ──▶ OpenAI
                                    │                        └──▶ orchestration.AnalysisAgent
                                                                    │
                                          orchestration.Planner (deterministic, no MCP, no src)
                                          orchestration.Executor ──▶ mcp.tools ──▶ mcp.adapters ──▶ src/* ──▶ SEC HTTP
                                                                                                    │
                                          services.artifact_service ──▶ storage/* ◀────────────────┘ (files → object store)
evaluation ──▶ src/* (fixtures)  and  ──▶ orchestration.AnalysisAgent (mocked)   and ──▶ backend models (persisted eval runs)
```

Key directional facts (enforced by the codebase today):

| From | To | Mechanism | Notes |
|---|---|---|---|
| API routes | services | direct calls via `deps.py` DI | routes raise `HTTPException` only at boundary |
| services | repositories/models | SQLAlchemy session | domain exceptions in `services/exceptions.py` |
| API **and** worker | `EdgarPipelineExecutionService` | shared | single execution path, `from_worker` flag |
| execution service | `agents.traceable_analysis_pipeline` | function call | linear plan→MCP→critic→report |
| agents | `orchestration.AnalysisAgent` | `coordinator` callable | injectable seam |
| orchestration Executor | `mcp.tools` | `_dispatch_mcp` (only gate) | Planner never touches MCP/`src` |
| mcp | `src/*` + `config` | `mcp/adapters.py` (only bridge) | no duplicated business logic |
| artifact delivery | `storage/resolver.open_reader` | streamed | no raw filesystem paths exposed |
| evaluation | `src/*`, `orchestration`, models | fixtures + mocks + persisted runs | offline default suite |

Coupling hot-spots (see §8): `edgar_project/orchestration/schemas.py` (EDGAR
vocabulary baked into the orchestration contract), `mcp/adapters.py` (single
EDGAR↔`src` bridge), `EdgarPipelineExecutionService` (EDGAR-named but is the
generic run driver), `meta_json.ai_agents` / `output_payload_json` (untyped JSON
UI contract).

---

## 4. Module classification (summary; full table in `domain-boundaries.md`)

- **Reusable unchanged** — `backend/api/{auth_deps,access_checks}`, `backend/auth`,
  `backend/security`, `backend/db`, `backend/storage/*`, `backend/observability/*`,
  `backend/models/{user,project,artifact,model_call,run_execution_job}`,
  `backend/worker/*`, `backend/services/{run_lifecycle,run_queue,artifact,user}`.
  These are source-agnostic already.
- **Reusable behind interfaces** — `EdgarPipelineExecutionService` (rename/abstract
  to a generic run driver), `traceable_analysis_pipeline` (generalize the fixed
  chain into an investigation loop), `AnalysisRun`/`RunStep`/`ToolCall`
  (input-agnostic once `role_key`/`tool_name` are not EDGAR-only), `critic_agent`,
  `report_agent`, `mcp` tool contract (`ToolResponseEnvelope`), evaluation runner.
- **EDGAR-specific** — all of `src/*`, `config.py`, `main.py`,
  `edgar_project/mcp/{adapters,tools}.py`, `edgar_project/demo/*`, EDGAR fixtures,
  `validation/manual_validation.csv`. **Preserve as first-party adapter.**
- **Orchestration-specific** — `edgar_project/orchestration/*` (Planner is
  deterministic template selection over EDGAR goal codes; contract is EDGAR-shaped).
- **Deprecate / consolidate** — top-level `orchestration/agent.py` (thin wrapper),
  stray `tmp_empty_uf.csv`, duplicate `frontend/pnpm-lock.yaml` (repo uses npm).

---

## 5. Domain entities vs persistence entities

The codebase does **not** currently separate domain entities from persistence.
"Domain" state is either Pydantic wire/contract models or untyped JSON blobs.

**Persistence entities** (SQLAlchemy, `backend/models/`):

| Model | Table | Purpose | Notable columns |
|---|---|---|---|
| `User` | `users` | auth principal | `email`, `hashed_password`, `is_admin` |
| `Project` | `projects` | run container | `owner_user_id`, `tickers` (**EDGAR-shaped**), `settings_json` |
| `AnalysisRun` | `analysis_runs` | one execution | `status`, `input_payload_json`, `output_payload_json`, `meta_json`, `correlation_id` |
| `RunStep` | `run_steps` | per-phase state | `step_index`, `status`, `planned_tool_name`, `meta_json` |
| `ToolCall` | `tool_calls` | executed MCP step | `tool_name`, `mcp_status`, `response_envelope_json`, `panel_row_count`/`anomaly_count` (**EDGAR-shaped counters**) |
| `ModelCall` | `model_calls` | LLM invocation audit | `provider`, `model_name`, `prompt_id`, `prompt_version`, tokens, latency |
| `Artifact` | `artifacts` | output bytes ref | `role_key`, `kind`, `storage_uri`, `content_sha256` (source-agnostic) |
| `RunExecutionJob` | `run_execution_jobs` | queue row | `status`, `claim_token`, `attempt_count`, `lease_expires_at` |
| `EvaluationRun` | `evaluation_runs` | benchmark run | `suite_id`, `summary_json`, `results_json` |
| `EvaluationCaseResult` | `evaluation_case_results` | per-case result | `input_mode`, `degradation_class`, `checks_json` |

**"Domain"/contract models** (Pydantic, not persisted as such):
`edgar_project/orchestration/schemas.py` — `OrchestrationInput`,
`InterpretedGoal`, `GoalPreferences`, `PlanTemplateSnapshot`,
`OrchestrationOutput`, `OrchestrationRunStatus`, etc. These carry EDGAR
vocabulary (tickers, anomaly, peer, margins) and are stored as JSON inside
`AnalysisRun.output_payload_json` / `input_payload_json`.

> New in-repo (additive, not yet wired): `agentic/domain/*` provides the
> input-agnostic entities (`DatasetManifest`, `InvestigationState`, `Hypothesis`,
> `Experiment`, `Evidence`) that a later phase maps onto persistence.

---

## 6. Existing schemas (run / artifact / critic / report / model-call / evaluation)

- **Run / API** — `backend/schemas/analysis_run.py`, `api_phase_a.py`
  (`AnalysisRunSummary/Detail`, `RunStepDetailItem`, `RunTraceShellResponse`),
  `run_lifecycle.py`, `run_progress.py`, `execute_run.py`, `prompt_routing.py`,
  `run_transparency.py`.
- **Artifact** — `backend/schemas/artifact.py`, `artifact_content.py`
  (`ArtifactMetadata`, `ArtifactPreviewResponse`); MCP-side `ArtifactSummary`,
  `TabularPreview` in `edgar_project/mcp/schemas.py`.
- **Critic** — `backend/agents/output_schemas.py:CriticAgentLLMOutput`; prompt in
  `backend/agents/prompts/critic`; persisted into `meta_json.ai_agents.critic`.
- **Report** — report LLM output schema in `backend/agents/output_schemas.py`;
  prompt in `backend/agents/prompts/report`; persisted into
  `output_payload_json.user_facing_report` and `meta_json.ai_agents.report`.
- **Model-call** — `backend/schemas/model_call.py`, `llm_usage.py`
  (`LlmRunUsageSummary`); persisted via `ModelCall`.
- **Evaluation** — `edgar_project/evaluation/schemas.py` (`BenchmarkInput`,
  `ExpectedArtifacts`, `ExpectedOrchestration`, `ExpectedFindings`,
  `ValidationPolicy`, `InputMode`, `ValidationDegradationClass`);
  `backend/schemas/evaluation_run.py`, `evaluation_case_result.py`.

The **critic/report/transparency UI contract is untyped JSON** in
`meta_json.ai_agents` and `output_payload_json`, parsed defensively on the
frontend (`frontend/src/lib/orchestration-output.ts`, `ai-agents-meta.ts`). This
is a generalization risk (§8).

---

## 7. Tests that protect important behavior

89 pytest modules + Vitest frontend suites. The ones that must stay green through
migration:

**Numerical / deterministic regression (highest value — the trust core):**
`tests/test_anomaly.py` (288 lines), `test_peer_signals.py`, `test_findings.py`,
`test_trend_breaks.py`, `test_metric_mapping.py`, `test_metric_coverage.py`,
`test_metric_caveats.py`, `test_data_quality.py`, `test_exclusions.py`,
`test_manual_validation.py`, `test_deterioration_focus.py`, `test_report_credibility.py`,
`tests/mcp/test_tools.py` (439 lines), `tests/mcp/test_schemas.py`,
`tests/mcp/test_adapters.py`, and the offline fixture suite
`edgar_project/evaluation/fixtures/*` + `suite_fixtures_v1`.

**Orchestration contract:** `tests/orchestration/test_contract_stability.py`,
`test_agent.py`, `test_phase3_orchestration.py`,
`tests/test_execution_handoff.py`, `tests/test_interpreted_goal_persistence.py`,
`tests/test_mcp_orchestration_artifact_contract.py`.

**Run lifecycle / worker / persistence:** `test_run_lifecycle_api.py`,
`test_run_lifecycle_production.py`, `test_async_run_queue.py`,
`test_worker_job_lifecycle*.py`, `test_worker_lease_heartbeat.py`,
`test_worker_attempt_history.py`, `test_run_isolation_*.py`,
`test_backend_foundation.py`, `test_run_repositories_services.py`.

**Auth / security / storage / delivery:** `test_auth_api.py`,
`test_secure_defaults_*.py`, `test_settings_database_posture.py`,
`test_artifact_storage*.py`, `test_artifact_content_*.py`, `test_retention_maintenance.py`.

**Agents / transparency:** `test_traceable_pipeline.py`, `test_llm_*`,
`test_critic_artifact_excerpts.py`, `test_context_budget.py`,
`test_model_routing.py`, `test_traceability_*`, `test_run_transparency_builders.py`.

**Evaluation:** `test_evaluation_*` (control plane, policy contract, runner
policy, CLI compat, live/hybrid).

> New: `tests/agentic/` (16 tests) covers the additive input-agnostic domain +
> adapter seam. These do not yet protect production behavior (nothing wired).

---

## 8. Architectural blockers to becoming input-agnostic

1. **EDGAR vocabulary in the orchestration contract.**
   `edgar_project/orchestration/schemas.py` fixes `tickers`, `InterpretedGoalCode`
   (anomaly/peer/etc.), `GoalPreferences` (margins, revenue_growth…),
   `ResolvedCompany(ticker, cik)`. Any non-EDGAR input cannot be expressed.
2. **`tickers` as a first-class field** on `OrchestrationInput`, `Project.tickers`,
   `AnalysisRunCreate`, chat scope, and route-preview. There is no dataset/manifest
   abstraction between "user scope" and "the pipeline".
3. **Single EDGAR bridge does all data acquisition.** `mcp/adapters.py` → `src/*`
   is the only way data enters the system; there is no adapter registry or
   `DatasetManifest` seam. (The new `agentic/adapters` package adds this seam but
   is not wired into orchestration yet.)
4. **Planner is EDGAR-template selection.** `Planner.build_plan` maps EDGAR goal
   codes to EDGAR plan templates; the executor dispatches a fixed set of EDGAR MCP
   tools (`_dispatch_mcp` hard-codes `resolve_company … run_pipeline`).
5. **EDGAR-shaped persistence columns.** `ToolCall.panel_row_count`,
   `feature_row_count`, `anomaly_count`, `report_character_count`;
   `Project.tickers`. These bias the schema toward one domain.
6. **Untyped UI contract.** `meta_json.ai_agents` and `output_payload_json`
   assume EDGAR phases (intent/planning/critic/report) and EDGAR summaries.
7. **Naming as coupling.** `EdgarPipelineExecutionService`,
   `run_traceable_edgar_pipeline` are the generic run driver but named EDGAR-only,
   discouraging reuse.

## 9. Architectural blockers to real adaptive agency

Per the project's definition of agency (execution varies by goal; experiments
chosen dynamically; intermediate results change next actions; hypotheses
supported/weakened/rejected; competing explanations tested; stop on sufficient
**or** insufficient evidence; decisions persisted as structured state):

1. **The pipeline is a fixed linear chain, not a loop.**
   `traceable_analysis_pipeline` always runs plan → MCP → critic → report exactly
   once. There is no iteration, no re-planning from results.
2. **Planning is one-shot and deterministic.** `Planner.build_plan` picks a
   template up front; the Executor runs that plan to completion. Intermediate MCP
   results do **not** feed back into plan selection.
3. **No hypothesis / experiment / evidence state.** Nothing in the run models
   represents a hypothesis being supported or rejected, or an experiment selected
   because of a prior result. `output_payload_json` is a terminal snapshot.
4. **No termination policy.** Runs end when the fixed chain finishes; there is no
   "sufficient evidence" vs "insufficient evidence" decision. `ModelCallStatus`
   docstring even calls the model runtime "reserved for future agent runtime".
5. **Critic cannot redirect execution.** The critic runs *after* all computation
   and only annotates; it cannot request another experiment.
6. **State lives in model context / JSON, not typed structured state.** The
   agent's reasoning is embedded in LLM prompts and untyped `meta_json`, so
   decisions are neither inspectable nor serializable as first-class entities.

> The additive `agentic/domain` package (InvestigationState / Hypothesis /
> Experiment / Evidence / TerminationDecision) exists precisely to remove blockers
> 3–6; wiring it into an iterative planner/evidence-updater loop is the agency work.

---

## 10. Highest-risk areas (feeds the migration plan)

- **Deterministic numerical layer (`src/*`) + its regression tests** — the trust
  core; any change risks silent numeric drift. Treat as frozen behind an adapter.
- **Run lifecycle + worker lease/finalize state machine** — correctness-critical
  concurrency; broad status/enum changes are dangerous.
- **`OrchestrationOutput` / `meta_json` JSON contract** — consumed by the frontend
  with defensive parsers; schema changes can silently blank the UI.
- **Auth + ownership (`access_checks`, `auth_deps`)** — must not weaken; 404-for-
  unauthorized behavior is a guarantee.
- **Alembic migrations** — any persistence mapping for investigation state must be
  reversible and additive.

See [`migration-plan.md`](./migration-plan.md) for the staged, regression-minimizing
sequence and the explicit preservation guarantees.
