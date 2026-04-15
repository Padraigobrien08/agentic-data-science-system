# Codebase Structure

**Analysis Date:** 2026-04-15

## Directory Layout

```text
agentic_data_science_system/
├── backend/                # FastAPI API, worker, DB models, services, LLM/traceability, storage
├── frontend/               # Next.js App Router UI and server-side API bridge
├── edgar_project/          # Deterministic CLI, orchestration package, MCP layer, evaluation harness
├── src/                    # Phase 1 EDGAR analytics pipeline and artifact writers
├── tests/                  # Python test suite for backend, orchestration, MCP, and analytics
├── alembic/                # Database migration environment and revision files
├── docs/                   # Local stack and API runbooks
├── data/                   # SEC cache, processed CSVs, artifacts, local object-store root, evaluation outputs
├── validation/             # Manual validation CSVs, examples, and templates
├── examples/               # Static example outputs for docs and demos
├── notebooks/              # Interactive notebook demos
├── scripts/                # Compose convenience wrapper and smoke checks
├── orchestration/          # Thin wrapper package that forwards to `edgar_project/orchestration`
├── config.py               # Repo-root Phase 1 config and data paths
├── main.py                 # Legacy direct pipeline entrypoint
└── docker-compose.yml      # Local full stack: db, migrate, api, worker, web
```

## Directory Purposes

**`backend/`:**
- Purpose: Host the API, background worker, persistence layer, traceability agents, artifact storage, and observability infrastructure.
- Contains: `backend/api/`, `backend/services/`, `backend/repositories/`, `backend/models/`, `backend/schemas/`, `backend/worker/`, `backend/agents/`, `backend/storage/`, `backend/observability/`
- Key files: `backend/main.py`, `backend/api/routes/runs.py`, `backend/services/edgar_pipeline_execution_service.py`, `backend/agents/traceable_analysis_pipeline.py`, `backend/worker/__main__.py`

**`backend/api/`:**
- Purpose: Keep HTTP-only concerns isolated from domain logic.
- Contains: router composition in `backend/api/router.py`, route modules in `backend/api/routes/`, auth dependencies in `backend/api/auth_deps.py`, ownership checks in `backend/api/access_checks.py`, DI wiring in `backend/api/deps.py`
- Key files: `backend/api/router.py`, `backend/api/routes/auth.py`, `backend/api/routes/projects.py`, `backend/api/routes/runs.py`, `backend/api/routes/artifacts.py`

**`backend/services/`:**
- Purpose: Hold business rules, orchestration coordination, lifecycle transitions, queue behavior, and artifact ingestion.
- Contains: run CRUD/lifecycle services, queueing services, artifact services, the persisted chat-completion wrapper, and the pipeline execution coordinator.
- Key files: `backend/services/analysis_run_service.py`, `backend/services/run_queue_service.py`, `backend/services/run_lifecycle_service.py`, `backend/services/artifact_service.py`, `backend/services/recorded_chat_completion_service.py`

**`backend/repositories/`:**
- Purpose: Hold persistence-only query helpers without lifecycle policy.
- Contains: repository classes that wrap SQLAlchemy access per aggregate or entity.
- Key files: `backend/repositories/analysis_run_repository.py`, `backend/repositories/run_step_repository.py`, `backend/repositories/run_execution_job_repository.py`

**`backend/models/`:**
- Purpose: Define the persisted relational model for projects, runs, steps, tool calls, model calls, artifacts, and queue jobs.
- Contains: SQLAlchemy models and enum/type helpers.
- Key files: `backend/models/project.py`, `backend/models/analysis_run.py`, `backend/models/run_step.py`, `backend/models/tool_call.py`, `backend/models/model_call.py`, `backend/models/artifact.py`, `backend/models/run_execution_job.py`

**`backend/schemas/`:**
- Purpose: Define HTTP wire models and derived summary/transparency views.
- Contains: request/response schemas, response-building helpers, health/transparency summaries, and execution override models.
- Key files: `backend/schemas/api_phase_a.py`, `backend/schemas/analysis_run.py`, `backend/schemas/run_transparency.py`, `backend/schemas/execute_run.py`, `backend/schemas/health.py`

**`backend/agents/`:**
- Purpose: Hold the traceable LLM phases and the helpers that persist prompt/version/model metadata alongside deterministic orchestration output.
- Contains: critic/report agents, prompt loaders/registries, context builders, phase-output builders, traceability helpers, and prompt markdown files under `backend/agents/prompts/`
- Key files: `backend/agents/traceable_analysis_pipeline.py`, `backend/agents/critic_agent.py`, `backend/agents/report_agent.py`, `backend/agents/persist_mcp_trace.py`, `backend/agents/prompt_registry.py`

**`backend/worker/`:**
- Purpose: Keep background polling and retry/finalization logic separate from synchronous request handling.
- Contains: worker entrypoint, loop, and failure classification.
- Key files: `backend/worker/__main__.py`, `backend/worker/loop.py`, `backend/worker/failure_classification.py`

**`backend/storage/` and `backend/observability/`:**
- Purpose: Centralize cross-cutting infrastructure rather than scattering it through services.
- Contains: local object-store implementation, URI resolution, tracing setup, logging setup, request middleware, and metrics helpers.
- Key files: `backend/storage/factory.py`, `backend/storage/local.py`, `backend/storage/resolver.py`, `backend/observability/middleware.py`, `backend/observability/logging.py`

**`frontend/`:**
- Purpose: Hold the Next.js web application.
- Contains: `frontend/src/app/` route tree, `frontend/src/components/` UI modules, `frontend/src/actions/` server actions, `frontend/src/lib/` fetch/auth/view-model helpers, and config like `frontend/package.json` and `frontend/tsconfig.json`
- Key files: `frontend/src/app/layout.tsx`, `frontend/src/app/projects/[projectId]/chat/page.tsx`, `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx`, `frontend/src/lib/api/client.ts`

**`frontend/src/app/`:**
- Purpose: Define route structure, layouts, and route handlers using the App Router.
- Contains: `page.tsx`, `layout.tsx`, and `route.ts` files for landing, auth, projects, runs, trace pages, artifact pages, and internal server-only proxy routes.
- Key files: `frontend/src/app/page.tsx`, `frontend/src/app/projects/[projectId]/layout.tsx`, `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`

**`frontend/src/actions/`:**
- Purpose: Keep server mutations close to the UI while still hiding credentials and backend origin details.
- Contains: login/register/logout, project creation/scope updates, and run creation/execution actions.
- Key files: `frontend/src/actions/auth.ts`, `frontend/src/actions/projects.ts`, `frontend/src/actions/runs.ts`

**`frontend/src/components/`:**
- Purpose: Group reusable UI by product surface instead of by primitive type.
- Contains: chat shell modules in `frontend/src/components/chat-shell/`, run answer UI in `frontend/src/components/runs/`, deep-dive trace panels in `frontend/src/components/trace/`, and shared status/technical UI in `frontend/src/components/ui/`
- Key files: `frontend/src/components/chat-shell/chat-shell.tsx`, `frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/trace/run-trace-experience.tsx`, `frontend/src/components/trace/artifact-detail-panel.tsx`

**`frontend/src/lib/`:**
- Purpose: Hold typed backend API clients, auth/session helpers, parsers, and derived view-model builders.
- Contains: API modules in `frontend/src/lib/api/`, auth helpers in `frontend/src/lib/auth/`, and run-trace/primary-answer derivation helpers in files like `frontend/src/lib/run-primary-view.ts`
- Key files: `frontend/src/lib/api/runs.ts`, `frontend/src/lib/api/projects.ts`, `frontend/src/lib/auth/session.ts`, `frontend/src/lib/orchestration-output.ts`, `frontend/src/lib/ai-agents-meta.ts`

**`edgar_project/`:**
- Purpose: Hold the active Python package for CLI orchestration, MCP tooling, demo scenarios, and evaluation.
- Contains: `edgar_project/orchestration/`, `edgar_project/mcp/`, `edgar_project/evaluation/`, `edgar_project/demo/`
- Key files: `edgar_project/cli.py`, `edgar_project/repo_layout.py`, `edgar_project/orchestration/agent.py`, `edgar_project/mcp/server.py`, `edgar_project/evaluation/runner.py`

**`edgar_project/orchestration/`:**
- Purpose: Keep deterministic request interpretation, plan selection, execution handoff, and executor state together as a standalone package.
- Contains: coordinator, planner, executor, schemas, constants, template selection, intent parsing, execution contract, and run logging.
- Key files: `edgar_project/orchestration/agent.py`, `edgar_project/orchestration/planner.py`, `edgar_project/orchestration/executor.py`, `edgar_project/orchestration/execution_contract.py`, `edgar_project/orchestration/state.py`

**`edgar_project/mcp/`:**
- Purpose: Expose the Phase 1 pipeline as validated tools and a stdio MCP server.
- Contains: tool schemas, adapter functions that import `src/*`, tool implementations, CLI, and server entrypoints.
- Key files: `edgar_project/mcp/adapters.py`, `edgar_project/mcp/tools.py`, `edgar_project/mcp/server.py`, `edgar_project/mcp/schemas.py`

**`edgar_project/evaluation/`:**
- Purpose: Keep benchmark fixtures, schemas, and evaluation runners separate from production execution code.
- Contains: runner/check modules, fixture definitions, regression goldens, suite files, and script wrappers.
- Key files: `edgar_project/evaluation/runner.py`, `edgar_project/evaluation/schemas.py`, `edgar_project/evaluation/orchestration_mocks.py`, `edgar_project/evaluation/scripts/run_suite.py`

**`src/`:**
- Purpose: Hold the original Phase 1 analytics pipeline and write-on-disk artifact generation code.
- Contains: one module per analytical concern plus the top-level `src/pipeline_runner.py`.
- Key files: `src/data_fetch.py`, `src/normalization.py`, `src/features.py`, `src/anomaly.py`, `src/findings.py`, `src/report.py`, `src/pipeline_runner.py`

**`tests/`:**
- Purpose: Hold Python test coverage across analytics, orchestration, MCP, backend API, worker lifecycle, and LLM traceability.
- Contains: focused suites such as `tests/orchestration/`, `tests/mcp/`, shared fixtures in `tests/fixtures/`, and broad backend/integration tests at the top level.
- Key files: `tests/test_api_phase_a.py`, `tests/test_traceable_pipeline.py`, `tests/orchestration/test_executor_boundary.py`, `tests/mcp/test_tools.py`

**`alembic/`:**
- Purpose: Track schema migrations for the backend database.
- Contains: migration environment config and revision scripts.
- Key files: `alembic/env.py`, `alembic/versions/001_initial_runs_and_evaluation_runs.py`, `alembic/versions/007_project_tickers.py`

**`data/`:**
- Purpose: Hold runtime caches and outputs used by the pipeline and local backend storage.
- Contains: SEC cache under `data/raw/`, processed CSVs under `data/processed/`, pipeline artifacts under `data/artifacts/`, object-store files under `data/artifact_storage/`, and evaluation outputs under `data/evaluation/`
- Key files: `data/README.md`

**`validation/`:**
- Purpose: Hold manual validation workflows and templates rather than mixing them into pipeline code.
- Contains: `validation/manual_validation.csv`, documentation, example candidate files, and template CSVs.
- Key files: `validation/README.md`, `validation/manual_validation.csv`, `validation/template/manual_validation_template.csv`

**`docs/`, `scripts/`, `examples/`, `notebooks/`:**
- Purpose: Keep operational docs, helper scripts, static examples, and interactive demos out of the executable packages.
- Contains: stack/auth/artifact docs, Compose smoke scripts, example outputs, and notebook demos.
- Key files: `docs/local-stack.md`, `docs/auth-api.md`, `scripts/stack`, `scripts/smoke-compose.sh`, `examples/report.example.md`, `notebooks/demo_edgar_pipeline.ipynb`

**`orchestration/`:**
- Purpose: Provide a thin developer-facing wrapper package for CLI compatibility.
- Contains: a single wrapper module plus package marker.
- Key files: `orchestration/agent.py`, `orchestration/__init__.py`

## Key File Locations

**Entry Points:**
- `backend/main.py`: FastAPI application factory and process startup hook
- `backend/worker/__main__.py`: background worker entrypoint
- `frontend/src/app/layout.tsx`: root Next.js shell
- `edgar_project/cli.py`: main Python CLI for runs, demos, and evaluation
- `edgar_project/mcp/server.py`: stdio MCP server entrypoint
- `main.py`: legacy direct pipeline script
- `orchestration/agent.py`: compatibility CLI wrapper around the active orchestration package

**Configuration:**
- `config.py`: repo-root analytics config and data paths
- `backend/config/settings.py`: env-driven backend/runtime settings
- `docker-compose.yml`: local multi-service stack
- `frontend/package.json`: frontend runtime and scripts
- `frontend/tsconfig.json`: frontend TypeScript path alias and compile settings
- `alembic/env.py`: migration environment

**Core Logic:**
- `backend/services/edgar_pipeline_execution_service.py`: persisted orchestration execution + artifact ingest
- `backend/agents/traceable_analysis_pipeline.py`: deterministic orchestration wrapped with persisted step/LLM traceability
- `edgar_project/orchestration/agent.py`: coordinator
- `edgar_project/orchestration/planner.py`: deterministic plan selection
- `edgar_project/orchestration/executor.py`: MCP-only execution
- `edgar_project/mcp/adapters.py`: only adapter layer that imports `src/*`
- `src/pipeline_runner.py`: Phase 1 pipeline orchestration and artifact writing

**Testing:**
- `tests/`: primary Python test suite
- `frontend/src/__tests__/`: frontend repo-level tests
- `frontend/src/lib/__tests__/`: frontend derivation/helper tests
- `frontend/src/components/trace/planning-transparency-panel.test.tsx`: component-level trace UI test

## Naming Conventions

**Files:**
- Python modules use `snake_case.py`: `backend/services/run_queue_service.py`, `backend/models/analysis_run.py`, `src/pipeline_runner.py`
- React components and frontend helpers use lowercase kebab-case: `frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/trace/agentic-trace-view.tsx`, `frontend/src/lib/run-trace-derive.ts`
- App Router reserved names stay literal: `frontend/src/app/**/page.tsx`, `frontend/src/app/**/layout.tsx`, `frontend/src/app/**/route.ts`, `frontend/src/middleware.ts`
- Compatibility wrappers keep the public command shape but point at the active implementation: `orchestration/agent.py`

**Directories:**
- Backend directories are layer names, not feature names: `backend/api/`, `backend/services/`, `backend/repositories/`, `backend/models/`, `backend/schemas/`
- Frontend route directories mirror URL structure: `frontend/src/app/projects/[projectId]/runs/[runId]/trace/`
- Frontend component directories are surface-oriented: `frontend/src/components/chat-shell/`, `frontend/src/components/runs/`, `frontend/src/components/trace/`
- Python package boundaries under `edgar_project/` represent subsystem boundaries: `edgar_project/orchestration/`, `edgar_project/mcp/`, `edgar_project/evaluation/`

## Where to Add New Code

**New backend API feature:**
- Primary code: add the route in `backend/api/routes/`, request/response schemas in `backend/schemas/`, business logic in `backend/services/`, and repository helpers in `backend/repositories/` only when queries become reusable.
- Tests: add Python tests under `tests/` or a focused subpackage like `tests/orchestration/` or `tests/mcp/` depending on scope.

**New persisted run concept or DB entity:**
- Primary code: add the SQLAlchemy model in `backend/models/`, migration in `alembic/versions/`, lifecycle/service logic in `backend/services/`, and wire models in `backend/schemas/`.
- Tests: add repository/service/API coverage under `tests/`.

**New orchestration behavior:**
- Primary code: update `edgar_project/orchestration/constants.py`, `edgar_project/orchestration/schemas.py`, `edgar_project/orchestration/planner.py`, and `edgar_project/orchestration/executor.py`.
- Place new executor-callable tools in `edgar_project/mcp/schemas.py` and `edgar_project/mcp/tools.py`; place the underlying numerical/data logic in `src/` and expose it through `edgar_project/mcp/adapters.py`.
- Do not put Phase 1 analytical code directly into `backend/services/` or `edgar_project/orchestration/executor.py`; the existing boundary routes that work through the MCP layer.

**New LLM traceability phase or prompt-driven feature:**
- Primary code: add the agent implementation under `backend/agents/`, prompt markdown under `backend/agents/prompts/<role>/`, prompt registration in `backend/agents/prompt_registry.py`, and persistence wiring in `backend/agents/traceable_analysis_pipeline.py`.
- Tests: add backend agent and traceability coverage under `tests/`.

**New frontend page or route:**
- Primary code: add the route under `frontend/src/app/` with `page.tsx` and optional `layout.tsx`; put reusable UI in `frontend/src/components/`; add server actions in `frontend/src/actions/` when a mutation is needed; add server-side fetch wrappers in `frontend/src/lib/api/`.
- Tests: add Vitest coverage near the relevant helper or component under `frontend/src/lib/__tests__/`, `frontend/src/components/**/__tests__/`, or `frontend/src/__tests__/`.

**New run-answer or deep-dive visualization:**
- Primary code: put view derivation logic in `frontend/src/lib/run-primary-view.ts`, `frontend/src/lib/run-trace-derive.ts`, or adjacent helper files; put rendering in `frontend/src/components/runs/`, `frontend/src/components/trace/`, or `frontend/src/components/transparency/`.
- Data source: prefer extending backend `output_payload_json`, `meta_json.ai_agents`, or typed summary responses in `backend/schemas/run_transparency.py` rather than parsing raw low-level payloads in the component.

**Utilities:**
- Shared backend domain helpers: `backend/domain/`
- Shared backend infrastructure helpers: `backend/observability/` or `backend/storage/`
- Shared frontend helpers: `frontend/src/lib/`
- Repo-root path/bootstrap helpers that must be importable before package setup: `config.py` or `edgar_project/repo_layout.py`

## Special Directories

**`frontend/.next/`:**
- Purpose: local Next.js build output
- Generated: Yes
- Committed: No

**`alembic/versions/`:**
- Purpose: ordered backend schema revisions
- Generated: No
- Committed: Yes

**`data/artifact_storage/`:**
- Purpose: local object-store root for persisted artifact bytes referenced by `backend/models/artifact.py`
- Generated: Yes
- Committed: No

**`backend/agents/prompts/`:**
- Purpose: versioned on-disk prompt templates used by critic/report/intent/planning-related agents
- Generated: No
- Committed: Yes

**`orchestration/`:**
- Purpose: wrapper namespace for developer CLI compatibility; active implementation still lives under `edgar_project/orchestration/`
- Generated: No
- Committed: Yes

---

*Structure analysis: 2026-04-15*
