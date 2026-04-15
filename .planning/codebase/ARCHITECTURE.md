# Architecture

**Analysis Date:** 2026-04-15

## Pattern Overview

**Overall:** Layered monorepo with a deterministic EDGAR analysis core, a traceable backend orchestration shell, and a server-rendered Next.js frontend.

**Key Characteristics:**
- Keep numerical EDGAR logic in `src/`; orchestration and API layers reach it through `edgar_project/mcp/adapters.py` and `edgar_project/mcp/tools.py` instead of importing `src/*` directly.
- Keep HTTP, auth, and ownership checks in `backend/api/`; route handlers delegate to `backend/services/`, which in turn use `backend/repositories/` and `backend/models/`.
- Keep UI data access on the server side in `frontend/src/lib/api/*.ts`, `frontend/src/actions/*.ts`, and `frontend/src/app/api/**/route.ts`; browser components are consumers of derived view models, not direct FastAPI clients.

## Layers

**Web UI / App Router shell:**
- Purpose: Render landing, auth, workspace chat, run answer, deep-dive trace, and artifact detail screens.
- Location: `frontend/src/app/`, `frontend/src/components/`, `frontend/src/actions/`, `frontend/src/lib/`
- Contains: pages such as `frontend/src/app/projects/[projectId]/chat/page.tsx` and `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, client shells such as `frontend/src/components/chat-shell/chat-shell.tsx`, server actions such as `frontend/src/actions/runs.ts`, and parsing/derivation helpers such as `frontend/src/lib/run-primary-view.ts`.
- Depends on: `frontend/src/lib/api/client.ts`, `frontend/src/lib/auth/session.ts`, `frontend/src/lib/orchestration-output.ts`, `frontend/src/lib/ai-agents-meta.ts`
- Used by: end users via the Next.js entrypoints in `frontend/src/app/layout.tsx` and `frontend/src/app/page.tsx`

**Frontend API bridge and auth boundary:**
- Purpose: Forward authenticated server-side requests from Next.js to FastAPI and keep JWTs out of browser JavaScript.
- Location: `frontend/src/lib/api/`, `frontend/src/lib/auth/`, `frontend/src/app/api/artifacts/`, `frontend/src/middleware.ts`
- Contains: shared request wrapper `frontend/src/lib/api/client.ts`, API modules like `frontend/src/lib/api/runs.ts`, bearer-header extraction in `frontend/src/lib/auth/backend-auth.ts`, and artifact proxy routes in `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`.
- Depends on: `API_URL` resolution in `frontend/src/lib/api/config.ts` and the HttpOnly session cookie defined in `frontend/src/lib/auth/constants.ts`
- Used by: server components, server actions, and middleware redirects

**HTTP API boundary:**
- Purpose: Expose authenticated project, run, artifact, auth, health, and metrics endpoints.
- Location: `backend/main.py`, `backend/api/router.py`, `backend/api/routes/`, `backend/api/auth_deps.py`, `backend/api/access_checks.py`
- Contains: FastAPI app construction in `backend/main.py`, top-level route registration in `backend/api/router.py`, thin handlers such as `backend/api/routes/runs.py` and `backend/api/routes/artifacts.py`, and owner-scoped checks in `backend/api/access_checks.py`.
- Depends on: dependency wiring in `backend/api/deps.py`, settings in `backend/config/settings.py`, service layer modules in `backend/services/`
- Used by: `frontend/src/lib/api/*.ts`, manual HTTP clients, Compose smoke checks, and tests under `tests/`

**Application service and persistence layer:**
- Purpose: Enforce lifecycle rules, coordinate DB state changes, and persist analysis artifacts and traces.
- Location: `backend/services/`, `backend/repositories/`, `backend/models/`, `backend/schemas/`, `backend/db/`
- Contains: orchestration execution in `backend/services/edgar_pipeline_execution_service.py`, run lifecycle logic in `backend/services/analysis_run_service.py` and `backend/services/run_lifecycle_service.py`, repository wrappers such as `backend/repositories/analysis_run_repository.py`, and ORM models such as `backend/models/analysis_run.py`.
- Depends on: SQLAlchemy session factory in `backend/db/session.py`, domain helpers in `backend/domain/`, object storage in `backend/storage/`
- Used by: API routes and the background worker

**Traceable backend orchestration layer:**
- Purpose: Wrap deterministic orchestration with persisted run steps, persisted MCP envelopes, optional critic/report LLM phases, and traceability metadata.
- Location: `backend/services/edgar_pipeline_execution_service.py`, `backend/agents/traceable_analysis_pipeline.py`, `backend/agents/persist_mcp_trace.py`, `backend/agents/`
- Contains: orchestration input construction, status transitions, `output_payload_json` persistence, `meta_json.ai_agents` enrichment, prompt registry lookups in `backend/agents/prompt_registry.py`, and optional LLM agent calls through `backend/services/recorded_chat_completion_service.py`.
- Depends on: `edgar_project/orchestration/agent.py`, `backend/services/run_step_service.py`, `backend/services/tool_call_service.py`, `backend/services/artifact_service.py`, `backend/llm/factory.py`
- Used by: synchronous `POST /v1/runs/{run_id}/execute` and the worker path in `backend/worker/loop.py`

**Deterministic orchestration core:**
- Purpose: Validate orchestration requests, pick a plan template, hand planning to execution, and emit a typed `OrchestrationOutput`.
- Location: `edgar_project/orchestration/`
- Contains: coordinator `edgar_project/orchestration/agent.py`, pure planner `edgar_project/orchestration/planner.py`, executor `edgar_project/orchestration/executor.py`, handoff contract `edgar_project/orchestration/execution_contract.py`, mutable runtime state `edgar_project/orchestration/state.py`, and public wire schemas in `edgar_project/orchestration/schemas.py`.
- Depends on: `edgar_project/mcp/tools.py` from the executor only; the planner intentionally avoids `src/*` and network dependencies.
- Used by: `edgar_project/cli.py`, `backend/agents/traceable_analysis_pipeline.py`, tests under `tests/orchestration/`, and the compatibility wrapper `orchestration/agent.py`

**MCP adapter and tool layer:**
- Purpose: Present the Phase 1 pipeline as deterministic tools and stdio MCP endpoints.
- Location: `edgar_project/mcp/`
- Contains: tool contracts in `edgar_project/mcp/schemas.py`, thin adapters in `edgar_project/mcp/adapters.py`, tool implementations in `edgar_project/mcp/tools.py`, stdio server in `edgar_project/mcp/server.py`, and local JSON CLI in `edgar_project/mcp/cli.py`.
- Depends on: `src/*`, `config.py`, repo-root path helpers, and data directories under `data/`
- Used by: `edgar_project/orchestration/executor.py`, external MCP clients, the evaluation mocks in `edgar_project/evaluation/orchestration_mocks.py`, and standalone MCP CLI usage

**Analytical pipeline layer:**
- Purpose: Fetch SEC data, normalize it, compute features and signals, detect anomalies, and write tabular/report artifacts.
- Location: `src/`, `config.py`, `main.py`
- Contains: data acquisition in `src/data_fetch.py`, panel building in `src/normalization.py`, features in `src/features.py`, anomaly detection in `src/anomaly.py`, peer and trend signals in `src/peer_signals.py` and `src/trend_breaks.py`, findings/report composition in `src/findings.py` and `src/report.py`, and orchestration/writers in `src/pipeline_runner.py`.
- Depends on: repo-root configuration in `config.py` and filesystem outputs under `data/raw/`, `data/processed/`, and `data/artifacts/`
- Used by: `main.py`, `edgar_project/mcp/adapters.py`, validation tooling in `src/manual_validation.py`, and the evaluation harness

**Async worker and queue layer:**
- Purpose: Execute queued runs in the background, reclaim stale leases, and retry transient failures.
- Location: `backend/worker/`, `backend/services/run_queue_service.py`, `backend/services/run_lifecycle_service.py`, `backend/models/run_execution_job.py`
- Contains: worker entrypoint `backend/worker/__main__.py`, polling/finalization loop `backend/worker/loop.py`, queue row creation in `backend/services/run_queue_service.py`, retry/cancel logic in `backend/services/run_lifecycle_service.py`, and queue persistence in `backend/repositories/run_execution_job_repository.py`.
- Depends on: the same execution service as the synchronous path, plus DB-backed lease state.
- Used by: `POST /v1/runs` when `enqueue_execution=true`, `POST /v1/runs/{run_id}/retry`, and the Compose `worker` service in `docker-compose.yml`

**Evaluation and benchmark layer:**
- Purpose: Run deterministic benchmark suites against fixtures or mocked orchestration flows.
- Location: `edgar_project/evaluation/`, `edgar_project/evaluation/scripts/`, `edgar_project/evaluation/fixtures/`
- Contains: the runner in `edgar_project/evaluation/runner.py`, benchmark/result schemas in `edgar_project/evaluation/schemas.py`, artifact/orchestration checks, golden regression helpers, and suite definitions under `edgar_project/evaluation/benchmarks/`.
- Depends on: `src/*` for fixture-based execution and `edgar_project/orchestration/agent.py` for orchestration-mocked cases.
- Used by: `python3 -m edgar_project.cli evaluate`, `python3 -m edgar_project.cli demo --fixtures`, and tests

**Storage and observability infrastructure:**
- Purpose: Provide object storage, structured logging, tracing, metrics, and request correlation.
- Location: `backend/storage/`, `backend/observability/`
- Contains: local object-store wiring in `backend/storage/factory.py` and `backend/storage/local.py`, artifact URI reading in `backend/storage/resolver.py`, request middleware in `backend/observability/middleware.py`, and structlog/OpenTelemetry setup in `backend/observability/logging.py` and `backend/observability/tracing.py`.
- Depends on: `backend/config/settings.py`
- Used by: API startup, worker startup, artifact delivery, and persisted traceability flows

## Data Flow

**Web run creation and review:**

1. `frontend/src/components/chat-shell/chat-shell.tsx` collects a workspace question and submits to the server action in `frontend/src/actions/runs.ts`.
2. `frontend/src/actions/runs.ts` calls `frontend/src/lib/api/runs.ts`, which uses `frontend/src/lib/api/client.ts` to forward the bearer token from `frontend/src/lib/auth/backend-auth.ts` to FastAPI.
3. `backend/api/routes/runs.py` creates an `AnalysisRun` row through `backend/services/analysis_run_service.py`; it either enqueues work through `backend/services/run_queue_service.py` or executes immediately through `backend/services/edgar_pipeline_execution_service.py`.
4. `backend/services/edgar_pipeline_execution_service.py` builds `OrchestrationInput`, moves the process to the repo root with `edgar_project/repo_layout.py`, and calls `backend/agents/traceable_analysis_pipeline.py`.
5. `backend/agents/traceable_analysis_pipeline.py` invokes `edgar_project/orchestration/agent.py`, persists executor steps to `RunStep` and `ToolCall` rows via `backend/agents/persist_mcp_trace.py`, optionally runs critic/report LLM phases, and patches `output_payload_json` with `user_facing_report` and `llm_phases_summary`.
6. `backend/services/edgar_pipeline_execution_service.py` ingests produced files through `backend/services/artifact_service.py`, enriches traceability artifact ids, transitions the final `AnalysisRun.status`, and commits.
7. `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx` and `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx` fetch the run, steps, artifacts, and model calls, then derive user-facing summaries through `frontend/src/lib/run-primary-view.ts`, `frontend/src/lib/orchestration-output.ts`, and `frontend/src/lib/run-trace-derive.ts`.

**Queued background execution:**

1. `backend/services/run_queue_service.py` or `backend/services/run_lifecycle_service.py` inserts a `RunExecutionJob` row and moves the parent run to `queued`.
2. `backend/worker/loop.py` claims the next runnable job using `backend/repositories/run_execution_job_repository.py`, restores trace context, and invokes the same `EdgarPipelineExecutionService.execute_analysis_run(..., from_worker=True)` path.
3. `backend/worker/loop.py` finalizes the job as completed, cancelled, requeued, or failed and may transition the run back to `queued` for retry on transient failures.

**CLI and MCP execution:**

1. `edgar_project/cli.py` validates CLI arguments and calls `edgar_project/orchestration.run_analysis_agent(...)`, or runs `edgar_project/evaluation/runner.py` for benchmark mode.
2. `edgar_project/orchestration/agent.py` asks `planner.py` for a plan, builds an `ExecutionRequest` from `execution_contract.py`, and hands it to `executor.py`.
3. `edgar_project/orchestration/executor.py` dispatches each planned step only through `edgar_project/mcp/tools.py`.
4. `edgar_project/mcp/tools.py` delegates the actual analytical work to `edgar_project/mcp/adapters.py`, which is the layer that imports `src/*` and `config.py`.
5. `src/pipeline_runner.py` and the surrounding `src/*` modules read SEC cache/input data, compute outputs, and write artifacts under `data/`.

**State Management:**
- Persistent product state lives in SQLAlchemy tables modeled by `backend/models/analysis_run.py`, `backend/models/run_step.py`, `backend/models/tool_call.py`, `backend/models/model_call.py`, `backend/models/artifact.py`, `backend/models/project.py`, and `backend/models/run_execution_job.py`.
- In-process orchestration state lives in `edgar_project/orchestration/state.py` as `OrchestrationRunState`; it is the executor’s scratch state and is converted back into `OrchestrationOutput`.
- Frontend transient state stays local to React components such as `frontend/src/components/chat-shell/chat-shell.tsx`; durable UI state is reloaded from backend resources instead of mirrored in a client store.

## Key Abstractions

**Analysis run aggregate:**
- Purpose: Represent one persisted execution attempt and its lifecycle.
- Examples: `backend/models/analysis_run.py`, `backend/services/analysis_run_service.py`, `backend/schemas/analysis_run.py`
- Pattern: A parent row owns child `RunStep`, `ToolCall`, `Artifact`, `ModelCall`, and `RunExecutionJob` records; routes surface compact views through `backend/schemas/api_phase_a.py`.

**Run-step trace model:**
- Purpose: Separate planned/executed step state from run-level outcome.
- Examples: `backend/models/run_step.py`, `backend/services/run_step_service.py`, `backend/agents/persist_mcp_trace.py`
- Pattern: Every visible execution phase becomes a `RunStep`; executed MCP steps also get a one-to-one `ToolCall`, while critic/report phases stay as LLM-flavored `RunStep` rows with rich `meta_json`.

**Orchestration handoff contract:**
- Purpose: Freeze the planner-to-executor boundary so execution can move out-of-process later without changing semantics.
- Examples: `edgar_project/orchestration/execution_contract.py`, `edgar_project/orchestration/state.py`, `edgar_project/orchestration/schemas.py`
- Pattern: `Planner` returns `PlanningOutcome`; `AnalysisAgent` converts it into `ExecutionRequest`; `Executor` returns `OrchestrationOutput`.

**MCP tool envelope:**
- Purpose: Normalize tool success, no-data, and error responses.
- Examples: `edgar_project/mcp/schemas.py`, `edgar_project/mcp/tools.py`, `edgar_project/orchestration/executor.py`
- Pattern: Tool functions never expose raw exceptions across the orchestration boundary; they return `ToolResponseEnvelope` with `status`, `message`, `data`, `artifacts`, and `errors`.

**Traceability metadata contract:**
- Purpose: Carry agent summaries and UI-facing audit slices without requiring the frontend to parse full prompts or envelopes.
- Examples: `backend/agents/traceable_analysis_pipeline.py`, `backend/schemas/run_transparency.py`, `frontend/src/lib/ai-agents-meta.ts`, `frontend/src/lib/orchestration-output.ts`
- Pattern: backend writes compact data into `analysis_run.meta_json["ai_agents"]` and `analysis_run.output_payload_json`; frontend parsing helpers derive typed UI models from those fields.

**Artifact storage abstraction:**
- Purpose: Decouple artifact bytes from DB rows and HTTP delivery.
- Examples: `backend/models/artifact.py`, `backend/services/artifact_service.py`, `backend/storage/local.py`, `backend/api/routes/artifacts.py`
- Pattern: pipeline files are ingested into an object store and referenced by `storage_uri`; HTTP handlers stream bytes or bounded previews without exposing raw filesystem paths to the browser.

## Entry Points

**Backend API:**
- Location: `backend/main.py`
- Triggers: `uvicorn backend.main:app`, Compose `api` service, test clients
- Responsibilities: configure logging/tracing, ensure storage/database prerequisites, mount `ObservabilityMiddleware`, and register `/health`, `/metrics`, and `/v1/*` routers

**Background worker:**
- Location: `backend/worker/__main__.py`
- Triggers: `python -m backend.worker`, Compose `worker` service
- Responsibilities: configure observability, report LLM readiness, optionally expose worker metrics, and start the DB-backed polling loop in `backend/worker/loop.py`

**Next.js web app:**
- Location: `frontend/src/app/layout.tsx`
- Triggers: `next dev`, `next build`, `next start`
- Responsibilities: load the current user server-side, render the global shell, and hand off per-route work to `page.tsx`, `layout.tsx`, and `route.ts` files under `frontend/src/app/`

**Deterministic CLI:**
- Location: `edgar_project/cli.py`
- Triggers: `python3 -m edgar_project.cli run`, `demo`, `evaluate`
- Responsibilities: normalize CLI arguments, run orchestration or benchmark flows, and print digests or JSON

**MCP stdio server:**
- Location: `edgar_project/mcp/server.py`
- Triggers: `python -m edgar_project.mcp.server` or `python -m edgar_project.mcp server`
- Responsibilities: expose MCP tool functions with validated arguments and JSON envelopes

**Legacy direct pipeline script:**
- Location: `main.py`
- Triggers: `python3 main.py`
- Responsibilities: run the Phase 1 pipeline directly against `config.DEFAULT_TICKERS` and write artifacts without the backend persistence shell

**Compatibility orchestration wrapper:**
- Location: `orchestration/agent.py`
- Triggers: `python -m orchestration.agent`
- Responsibilities: provide a thin developer-facing wrapper around `edgar_project.orchestration`

## Error Handling

**Strategy:** Convert boundary failures into typed HTTP, orchestration, or MCP response objects close to the boundary, and persist enough structured detail for later trace inspection.

**Patterns:**
- FastAPI routes such as `backend/api/routes/runs.py` and `backend/api/routes/artifacts.py` translate service errors into `HTTPException` responses; ownership checks in `backend/api/access_checks.py` deliberately return `404` for both missing and unauthorized resources.
- Service-layer transition rules live in `backend/services/analysis_run_service.py`, `backend/services/run_lifecycle_service.py`, `backend/services/run_step_service.py`, and `backend/services/tool_call_service.py`; invalid state changes raise typed exceptions instead of silently mutating rows.
- MCP tools in `edgar_project/mcp/tools.py` wrap validation, SEC request, file, and internal failures into `ToolResponseEnvelope` responses with structured `errors[]`.
- Orchestration aggregates typed warnings/errors into `OrchestrationOutput` in `edgar_project/orchestration/executor.py` rather than relying on logs alone.
- Worker execution in `backend/worker/loop.py` distinguishes terminal failures, transient failures, cancellations, and stale-lease recovery before deciding whether to requeue a job.

## Cross-Cutting Concerns

**Logging:** Structured JSON logging and request correlation are installed by `backend/observability/logging.py` and `backend/observability/middleware.py`; orchestration and worker flows add `run_id`, `analysis_run_id`, and trace fields to logs.

**Validation:** Request and response contracts are strongly typed with Pydantic in `backend/schemas/`, `edgar_project/orchestration/schemas.py`, and `edgar_project/mcp/schemas.py`; Next.js code consumes typed wire helpers in `frontend/src/lib/api/types.ts` and parsing modules under `frontend/src/lib/`.

**Authentication:** Backend auth is JWT bearer based through `backend/api/auth_deps.py`, `backend/auth/tokens.py`, and `backend/api/routes/auth.py`; the frontend stores the JWT in the HttpOnly cookie from `frontend/src/actions/auth.ts` and guards workspace routes with `frontend/src/middleware.ts`.

---

*Architecture analysis: 2026-04-15*
