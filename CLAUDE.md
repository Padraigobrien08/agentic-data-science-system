<!-- GSD:project-start source:PROJECT.md -->
## Project

**Agentic Data Science System**

Agentic Data Science System is an auditable agentic analysis platform over tabular data, with SEC EDGAR as the flagship dataset. It combines an adaptive investigation loop (`agentic/`), a deterministic financial-analysis pipeline (`src/`), a FastAPI backend, a background worker, two MCP servers, and a Next.js web app.

**Core Value:** Every run must produce trustworthy, isolated, auditable results the user can inspect without ambiguity — every claim links to evidence, every experiment has typed inputs and outputs, every run is reproducible from persisted structured state.

**Governing invariant:** the LLM plans and interprets; deterministic code computes. No number in a trace comes from a language model.

**Current direction:** hosted showcase demo — see [`docs/decisions/2026-08-11-showcase-direction.md`](docs/decisions/2026-08-11-showcase-direction.md) for the active plan and [`docs/demo-script.md`](docs/demo-script.md) for the narrative it serves. That decisions file supersedes sequencing in `.planning/`.

### Constraints

- **Tech stack**: Keep the existing Python + FastAPI + SQLAlchemy + Next.js + Postgres architecture — hardening should preserve established surfaces instead of forcing a rewrite
- **Brownfield safety**: Prefer explicit seams and incremental migrations over invasive refactors — the current product already has working CLI, MCP, backend, and frontend flows
- **Deterministic analysis**: Preserve the non-LLM numerical path in `src/` — run trust depends on keeping deterministic EDGAR computations inspectable. `agentic/domain` stays free of SQLAlchemy, and `agentic/` emits no logs/metrics directly (instrumentation goes through the `AgentObserver` seam)
- **Honest outcomes**: Uncertainty and failure are valid results. `insufficient_evidence` and `rejected` hypotheses must surface as first-class outcomes, never as errors or silent degradation
- **Compatibility**: Avoid breaking existing run APIs, artifact access patterns, and local development workflows unless a migration path is introduced — operators already rely on the current surfaces
- **Security**: Defaults must be safe in deployed environments — current permissive defaults are acceptable for local development only
- **Operational clarity**: Health, metrics, and retained run data must reflect real system state — false green signals are worse than noisy failures
<!-- GSD:project-end -->

<!-- GSD:stack-start source:codebase/STACK.md -->
## Technology Stack

## Languages
- Python 3.12+ - Backend API, worker, orchestration, MCP server, evaluation tooling, and the Phase 1 EDGAR pipeline live in `backend/`, `edgar_project/`, `src/`, and `main.py`.
- TypeScript - The web app, server actions, route handlers, and frontend tests live in `frontend/src/`, with config in `frontend/next.config.ts`, `frontend/tsconfig.json`, and `frontend/vitest.config.ts`.
- SQL / migration DSL - Relational schema and migrations are maintained through `backend/models/` and `alembic/versions/`.
- Bash - Local stack wrappers and smoke checks live in `scripts/stack` and `scripts/smoke-compose.sh`.
- Dockerfile / Compose YAML - Container build and local deployment definitions live in `Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml`.
- Markdown / Jupyter - Operational docs and demo notebooks live in `docs/`, `README.md`, and `notebooks/demo_edgar_pipeline.ipynb`.
## Runtime
- CPython 3.12 - The backend container uses `python:3.12-slim-bookworm` in `Dockerfile`; CI also installs Python 3.12 in `.github/workflows/ci.yml`.
- Node.js 22 for containerized frontend - `frontend/Dockerfile` uses `node:22-bookworm-slim`.
- Node.js 20 in CI - `.github/workflows/ci.yml` runs the frontend job with Node 20.
- Browser + Next.js server runtime - The App Router web UI runs from `frontend/src/app/`, with server-only API calls in `frontend/src/lib/api/` and `frontend/src/actions/`.
- Python: `pip` (version not pinned) using `requirements.txt`, `requirements-backend.txt`, and `requirements-dev.txt`.
- Python lockfile: missing. Dependency resolution is requirements-based, not lockfile-based.
- Frontend: `npm` (version not pinned) using `frontend/package.json`.
- Lockfile: present at `frontend/package-lock.json`.
- Additional lockfile present: `frontend/pnpm-lock.yaml` exists, but CI, Docker, and docs all use `npm`, not `pnpm`.
## Frameworks
- FastAPI `>=0.115.0` - Main HTTP API in `backend/main.py`, with route modules in `backend/api/routes/`.
- SQLAlchemy `>=2.0.36` - ORM and session layer in `backend/db/session.py`, `backend/models/`, and repository/service code under `backend/repositories/` and `backend/services/`.
- Alembic `>=1.14.0` - Schema migrations configured in `alembic/env.py` with revision files in `alembic/versions/`.
- Pydantic 2 + `pydantic-settings` - Request/response schemas and env-driven settings in `backend/schemas/`, `edgar_project/*/schemas.py`, and `backend/config/settings.py`.
- Next.js `^15.1.0` - App Router frontend in `frontend/src/app/`, with build/runtime config in `frontend/next.config.ts`.
- React `^19.0.0` - UI component layer in `frontend/src/components/` and page composition in `frontend/src/app/`.
- FastMCP / MCP SDK `mcp>=1.0` - Stdio MCP server in `edgar_project/mcp/server.py` and local MCP CLI in `edgar_project/mcp/cli.py`.
- `pytest>=8.0` - Backend and orchestration test suite under `tests/`, invoked in `.github/workflows/ci.yml`.
- Vitest `^2.1.9` - Frontend unit tests in `frontend/src/__tests__/` and `frontend/src/lib/__tests__/`, configured by `frontend/vitest.config.ts`.
- Testing Library + jsdom - Frontend component/runtime testing via `@testing-library/react`, `@testing-library/dom`, and `jsdom` from `frontend/package.json`.
- Uvicorn `>=0.30.0` - ASGI server for the FastAPI app, launched from `Dockerfile` and `docs/local-stack.md`.
- Docker Compose - Recommended full-stack orchestration documented in `docs/local-stack.md` and wrapped by `scripts/stack`.
- Tailwind CSS `^3.4.16` - Utility styling configured in `frontend/tailwind.config.ts` and used from `frontend/src/app/globals.css`.
- ESLint `^9.16.0` with `eslint-config-next` - Frontend linting from `frontend/.eslintrc.json` and `.github/workflows/ci.yml`.
- Turbopack - Local frontend development uses `next dev --turbopack` in `frontend/package.json`.
## Key Dependencies
- `pandas>=2.0` - Core dataframe pipeline for normalization, features, reporting, and evaluation in files such as `src/anomaly.py`, `src/report.py`, and `edgar_project/evaluation/analytical_checks.py`.
- `numpy>=1.24` - Numerical computations in the anomaly and peer-signal layers, e.g. `src/anomaly.py` and `src/peer_signals.py`.
- `requests>=2.28` - External SEC HTTP access in `src/data_fetch.py` and error handling adapters in `edgar_project/mcp/adapters.py`.
- `openai>=1.40.0` - Optional LLM provider for intent, planning, critic, and report phases in `backend/llm/openai_provider.py` and `backend/llm/factory.py`.
- `PyJWT>=2.8.0` - HS256 JWT issue/verify logic in `backend/auth/tokens.py` and `backend/api/auth_deps.py`.
- `bcrypt>=4.1.0` - Password hashing and verification in `backend/security/passwords.py`.
- `react-markdown^10.1.0` - Markdown artifact rendering in `frontend/src/components/runs/markdown-report.tsx`.
- `psycopg2-binary>=2.9.9` - Postgres connectivity behind `EDGAR_BACKEND_DATABASE_URL`, used through SQLAlchemy in `backend/db/session.py`.
- `structlog>=24.4.0` - Structured JSON logging in `backend/observability/logging.py`, used by API, worker, and services such as `backend/services/edgar_pipeline_execution_service.py`.
- `prometheus-client>=0.21.0` - API and worker metrics in `backend/api/routes/metrics.py`, `backend/worker/__main__.py`, and `backend/observability/metrics.py`.
- `opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-exporter-otlp-proto-http` - Trace propagation/export in `backend/observability/tracing.py` and executor tracing in `edgar_project/orchestration/executor.py`.
- `email-validator>=2.0.0` - Email field validation for auth schemas under `backend/schemas/auth.py` and `backend/schemas/user.py`.
## Configuration
- Backend settings are centralized in `backend/config/settings.py` via `BaseSettings` with env prefix `EDGAR_BACKEND_` and repo-root env file support (`env_file=".env"`).
- Frontend server-side backend origin is read from `API_URL` in `frontend/src/lib/api/config.ts`.
- Optional public frontend shortcut config uses `NEXT_PUBLIC_DEFAULT_PROJECT_ID` in `frontend/src/lib/landing-project.ts`.
- OpenAI credentials can come from `EDGAR_BACKEND_OPENAI_API_KEY` or fallback `OPENAI_API_KEY`, as implemented in `backend/config/settings.py`.
- Local env files are present but were not read: repo-root `.env`, repo-root `.env.example`, and `frontend/.env.example`.
- High-value backend config knobs include `EDGAR_BACKEND_DATABASE_URL`, `EDGAR_BACKEND_ALLOW_SQLITE`, `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION`, `EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT`, `EDGAR_BACKEND_LLM_PROVIDER`, `EDGAR_BACKEND_WORKER_METRICS_PORT`, and the `EDGAR_BACKEND_AGENT_*` model/prompt/context fields declared in `backend/config/settings.py`.
- Observability config uses `OTEL_SERVICE_NAME`, `OTEL_TRACES_EXPORTER`, `EDGAR_BACKEND_OTEL_TRACES_EXPORTER`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` in `backend/observability/tracing.py`.
- Backend image build is defined in `Dockerfile`; frontend image build is defined in `frontend/Dockerfile`.
- Local multi-service startup is documented in `docs/local-stack.md` and represented in `docker-compose.yml`.
- Database migrations load runtime settings from `backend/config/settings.py` through `alembic/env.py`.
- Frontend build/runtime config lives in `frontend/next.config.ts`, `frontend/tailwind.config.ts`, `frontend/tsconfig.json`, and `frontend/.eslintrc.json`.
- CI build/test entrypoints live in `.github/workflows/ci.yml` and `.github/workflows/compose-smoke.yml`.
## Platform Requirements
- Python 3.12+ with `pip` and repo-root `PYTHONPATH=.` for backend CLI/API/worker flows, as documented in `README.md` and `docs/local-stack.md`.
- Node.js 22+ for local frontend development, per `docs/local-stack.md`; Node 20 is sufficient for CI in `.github/workflows/ci.yml`.
- Docker Compose v2.20+ for the documented full stack, per `docs/local-stack.md`.
- Writable local filesystem access to `data/`, `data/artifact_storage/`, and migration state under `alembic/`.
- The documented deployment target is a self-hosted container stack built from `Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml`.
- Backend production posture is Postgres-backed, with `EDGAR_BACKEND_ALLOW_SQLITE=false` recommended by `backend/config/settings.py` and `docs/local-stack.md`.
- A separate worker process is part of the supported runtime model, launched via `python -m backend.worker` or the Compose `worker` service described in `docs/local-stack.md`.
- Shared artifact storage is a filesystem path or Docker volume mounted into both API and worker processes, as described by `backend/storage/local.py` and `docs/local-stack.md`.
- No cloud-specific deployment target, Terraform, Kubernetes manifests, or managed-hosting adapter is detected in the repository.
<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->
## Conventions

## Naming Patterns
- Use `snake_case.py` for Python modules in `backend/`, `edgar_project/`, and `tests/` (examples: `backend/services/run_lifecycle_service.py`, `backend/models/analysis_run.py`, `tests/test_run_lifecycle_api.py`).
- Use lowercase `kebab-case.ts` / `kebab-case.tsx` for frontend utilities and components under `frontend/src/` (examples: `frontend/src/lib/run-pipeline-phases.ts`, `frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/transparency/report-evidence-panel.tsx`).
- Use framework-reserved filenames only where Next.js expects them: `frontend/src/app/**/page.tsx`, `frontend/src/app/**/layout.tsx`, and `frontend/src/app/api/**/route.ts`.
- Use `index.ts` barrels only inside established frontend subpackages such as `frontend/src/components/structured-answer/index.ts` and `frontend/src/lib/api/index.ts`; Python package surfaces use thin `__init__.py` re-exports such as `backend/services/__init__.py`.
- Use `snake_case` for Python functions and methods (`backend/main.py:create_app`, `backend/services/run_lifecycle_service.py:cancel_analysis_run`, `backend/services/analysis_run_service.py:transition_status`).
- Use `camelCase` for TypeScript helpers and `PascalCase` for React components (`frontend/src/lib/api/client.ts:apiGet`, `frontend/src/lib/run-pipeline-phases.ts:derivePipelinePhaseView`, `frontend/src/components/runs/run-primary-answer.tsx:RunPrimaryAnswer`).
- Prefer verb-led names for mutations (`merge_output_payload`, `retry_analysis_run`, `parseArtifactRefs`) and derivation-style names for pure view builders (`deriveCurrentPhaseIndex`, `build_status_view`, `buildPrimaryAnswerView`).
- Use `snake_case` locals and parameters in Python, `camelCase` in TypeScript, and preserve domain acronyms inline (`analysis_run_id`, `runId`, `llmProvider`, `apiClient`).
- Reserve module constants for uppercase or underscore-prefixed uppercase tables (`backend/domain/status_transitions.py:_ANALYSIS_RUN_ALLOWED`, `frontend/src/lib/run-pipeline-phases.ts:PIPELINE_PHASES`, `frontend/src/app/projects/[projectId]/runs/[runId]/page.tsx:EXECUTABLE_HINT`).
- Keep JSON-like blobs explicitly named with `_json` or descriptive suffixes when they cross API/storage boundaries (`meta_json`, `input_payload_json`, `trace_context_json`).
- Use `PascalCase` for Python classes, ORM models, and Pydantic schemas (`Settings`, `AnalysisRun`, `RunEnqueueOverrides`, `AnalysisRunRead`).
- Use `PascalCase` for TypeScript interfaces, type aliases, and component prop models (`ArtifactMetadata`, `RunStepDetail`, `PipelinePhaseView`, `Props` blocks in `frontend/src/components/*`).
- Prefer explicit string-literal unions and typed wire mirrors over loose strings in frontend API code (`frontend/src/lib/api/types.ts`).
## Code Style
- Python source follows Black-like layout even though no repo formatter config is detected. `pyproject.toml`, `ruff.toml`, `.flake8`, `.isort.cfg`, `.editorconfig`, and `.prettierrc*` are not present at repo root, so match the existing 4-space indentation, trailing commas in multiline literals, and typed signatures seen in `backend/main.py`, `backend/services/analysis_run_service.py`, and `backend/repositories/run_execution_job_repository.py`.
- Frontend TypeScript/TSX uses 2-space indentation, semicolons, and wrapped JSX props/children as seen in `frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/trace/planning-transparency-panel.tsx`, and `frontend/src/components/transparency/report-evidence-panel.tsx`.
- Keep Python module docstrings at the top of files and use short JSDoc blocks only where the contract is subtle (`frontend/src/lib/run-pipeline-phases.ts`, `frontend/src/lib/api/types.ts`).
- Frontend linting is enforced by `frontend/.eslintrc.json` extending `next/core-web-vitals` and by `frontend/package.json` scripts such as `npm run lint`.
- No dedicated backend lint or static-analysis command is configured in repo config or `.github/workflows/ci.yml`; backend quality currently relies on typed code plus `pytest`.
- Keep suppressions narrow and justified. Existing examples are side-effect imports for ORM metadata (`import backend.models  # noqa: F401` in `tests/test_backend_foundation.py`), defensive boundary catches (`# noqa: BLE001` in `backend/api/routes/health.py`), and environment-only branches (`# pragma: no cover` in `backend/llm/openai_provider.py`).
## Import Organization
- Use the `@/*` alias defined in `frontend/tsconfig.json` for frontend app imports (`@/components/...`, `@/lib/...`).
- Backend code uses package-root imports (`backend.*`, `edgar_project.*`) instead of deep relative imports across layers.
- In tests that need SQLAlchemy metadata registered, import `backend.models` once near the top before creating tables (`tests/test_backend_foundation.py`, `tests/test_run_lifecycle_api.py`, `tests/test_async_run_queue.py`).
## Error Handling
- Raise domain/service exceptions inside backend services, not HTTP exceptions. `backend/services/exceptions.py` defines `InvalidStatusTransition` and `RunLifecycleError`; callers convert them at the API boundary.
- Translate service errors with rollback before re-raising. `backend/api/routes/runs.py` catches `RunLifecycleError` / `InvalidStatusTransition`, calls `db.rollback()`, and maps them to `HTTPException`.
- Use safe parsers and guard helpers for unknown JSON-like frontend payloads. `frontend/src/lib/run-pipeline-phases.ts:metaRecord`, `frontend/src/components/transparency/report-evidence-panel.tsx:isRecord`, and `frontend/src/components/trace/planning-transparency-panel.tsx:stringList` all return fallbacks instead of throwing on malformed shapes.
- Wrap failed backend HTTP calls in `ApiError` from `frontend/src/lib/api/errors.ts`; `frontend/src/lib/api/client.ts` reads the response body once and throws `new ApiError(status, body)` on non-2xx.
- In tests, prefer `with pytest.raises(...)` and message matching over manual try/except (`tests/test_execution_handoff.py`, `tests/test_llm_provider.py`, `tests/test_run_repositories_services.py`).
## Logging
- Configure logging once through `backend/observability/logging.py:setup_observability_logging`; JSON logs are the default from `backend/config/settings.py`.
- Acquire loggers with `structlog.get_logger(__name__)` or a scoped name (`backend/services/edgar_pipeline_execution_service.py`, `backend/worker/loop.py`, `backend/worker/__main__.py`).
- Emit event-style messages with structured fields instead of interpolated prose:
- Bind request/run trace context before long-running work via `bind_current_trace_for_logs()` and the middleware helpers in `backend/observability/middleware.py` and `backend/observability/tracing.py`.
## Comments
- Keep module-level Python docstrings that explain the boundary or purpose of the file (`backend/main.py`, `backend/services/run_lifecycle_service.py`, `tests/test_backend_foundation.py`).
- Use short explanatory comments for invariants, environment quirks, or boundary behavior, not line-by-line narration (`backend/config/settings.py`, `tests/test_api_phase_a.py`, `frontend/src/lib/run-pipeline-phases.ts`).
- Avoid adding new TODO/FIXME comments to product code unless there is a concrete follow-up artifact. Existing TODOs are limited to evaluation scaffolding such as `edgar_project/evaluation/runner.py`.
- Use concise JSDoc on exported frontend constants/components whose contract is not obvious (`frontend/src/lib/run-pipeline-phases.ts`, `frontend/src/components/trace/planning-transparency-panel.tsx`, `frontend/src/lib/api/types.ts`).
- Do not add heavyweight docblocks to every helper; most small local guard functions stay undocumented.
## Function Design
- Backend constructors and mutating methods prefer explicit type hints and keyword-only optional dependencies (`backend/services/run_lifecycle_service.py`, `backend/services/analysis_run_service.py`, `backend/repositories/run_execution_job_repository.py`).
- Frontend components declare a typed `Props` object and pass structured values rather than loose dictionaries (`frontend/src/components/runs/run-primary-answer.tsx`, `frontend/src/components/transparency/report-evidence-panel.tsx`).
- Unknown JSON from API/meta payloads is narrowed locally with guard helpers before use rather than cast globally.
- Backend services usually return ORM rows or typed tuples after flushing (`AnalysisRunService.transition_status`, `RunLifecycleService.build_status_view`, `RunExecutionJobRepository.queue_observability_snapshot`).
- Frontend helpers return explicit typed view models (`PipelinePhaseView`, `RunTransparencySummary`, `PrimaryAnswerView`) instead of mutating arguments in place.
- Use `None` / `null` sentinel returns only for expected absence (`get`, `metaRecord`, `parseArtifactRefs`), not for control-flow errors.
## Module Design
- Python packages expose thin curated re-exports from `__init__.py` only where the package is used as a public surface (`backend/services/__init__.py`).
- Frontend modules overwhelmingly use named exports; keep default exports for Next.js route modules like `frontend/src/app/**/page.tsx`.
- Keep backend data contracts split by responsibility: persistence models under `backend/models/`, wire schemas under `backend/schemas/`, repositories under `backend/repositories/`, and business workflows under `backend/services/`.
- Use barrels selectively in frontend feature folders that already present a stable surface (`frontend/src/components/structured-answer/index.ts`, `frontend/src/lib/api/index.ts`).
- Do not introduce broad repo-wide barrels for Python code; explicit imports are the norm.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->
## Architecture

## Pattern Overview
- Keep numerical EDGAR logic in `src/`; orchestration and API layers reach it through `edgar_project/mcp/adapters.py` and `edgar_project/mcp/tools.py` instead of importing `src/*` directly.
- Keep HTTP, auth, and ownership checks in `backend/api/`; route handlers delegate to `backend/services/`, which in turn use `backend/repositories/` and `backend/models/`.
- Keep UI data access on the server side in `frontend/src/lib/api/*.ts`, `frontend/src/actions/*.ts`, and `frontend/src/app/api/**/route.ts`; browser components are consumers of derived view models, not direct FastAPI clients.
## Layers
- Purpose: Render landing, auth, workspace chat, run answer, deep-dive trace, and artifact detail screens.
- Location: `frontend/src/app/`, `frontend/src/components/`, `frontend/src/actions/`, `frontend/src/lib/`
- Contains: pages such as `frontend/src/app/projects/[projectId]/chat/page.tsx` and `frontend/src/app/projects/[projectId]/runs/[runId]/trace/page.tsx`, client shells such as `frontend/src/components/chat-shell/chat-shell.tsx`, server actions such as `frontend/src/actions/runs.ts`, and parsing/derivation helpers such as `frontend/src/lib/run-primary-view.ts`.
- Depends on: `frontend/src/lib/api/client.ts`, `frontend/src/lib/auth/session.ts`, `frontend/src/lib/orchestration-output.ts`, `frontend/src/lib/ai-agents-meta.ts`
- Used by: end users via the Next.js entrypoints in `frontend/src/app/layout.tsx` and `frontend/src/app/page.tsx`
- Purpose: Forward authenticated server-side requests from Next.js to FastAPI and keep JWTs out of browser JavaScript.
- Location: `frontend/src/lib/api/`, `frontend/src/lib/auth/`, `frontend/src/app/api/artifacts/`, `frontend/src/middleware.ts`
- Contains: shared request wrapper `frontend/src/lib/api/client.ts`, API modules like `frontend/src/lib/api/runs.ts`, bearer-header extraction in `frontend/src/lib/auth/backend-auth.ts`, and artifact proxy routes in `frontend/src/app/api/artifacts/[artifactId]/content/route.ts`.
- Depends on: `API_URL` resolution in `frontend/src/lib/api/config.ts` and the HttpOnly session cookie defined in `frontend/src/lib/auth/constants.ts`
- Used by: server components, server actions, and middleware redirects
- Purpose: Expose authenticated project, conversation, run, investigation, evaluation, artifact, auth, health, and metrics endpoints.
- Location: `backend/main.py`, `backend/api/router.py`, `backend/api/routes/`, `backend/api/auth_deps.py`, `backend/api/access_checks.py`
- Contains: FastAPI app construction in `backend/main.py`, top-level route registration in `backend/api/router.py`, thin handlers such as `backend/api/routes/runs.py`, `backend/api/routes/investigations.py`, `backend/api/routes/conversations.py`, `backend/api/routes/evaluations.py`, and `backend/api/routes/artifacts.py`, plus owner-scoped checks in `backend/api/access_checks.py`. Security middleware lives in `backend/api/security_headers.py` and `backend/api/rate_limit.py`; ops routes (`/metrics`, `/v1/worker/health`) sit behind `OpsTokenDep`.
- Depends on: dependency wiring in `backend/api/deps.py`, settings in `backend/config/settings.py`, service layer modules in `backend/services/`
- Used by: `frontend/src/lib/api/*.ts`, manual HTTP clients, Compose smoke checks, and tests under `tests/`
- Purpose: Enforce lifecycle rules, coordinate DB state changes, and persist analysis artifacts and traces.
- Location: `backend/services/`, `backend/repositories/`, `backend/models/`, `backend/schemas/`, `backend/db/`
- Contains: orchestration execution in `backend/services/edgar_pipeline_execution_service.py`, run lifecycle logic in `backend/services/analysis_run_service.py` and `backend/services/run_lifecycle_service.py`, repository wrappers such as `backend/repositories/analysis_run_repository.py`, and ORM models such as `backend/models/analysis_run.py`.
- Depends on: SQLAlchemy session factory in `backend/db/session.py`, domain helpers in `backend/domain/`, object storage in `backend/storage/`
- Used by: API routes and the background worker
- Purpose: Wrap deterministic orchestration with persisted run steps, persisted MCP envelopes, optional critic/report LLM phases, and traceability metadata.
- Location: `backend/services/edgar_pipeline_execution_service.py`, `backend/agents/traceable_analysis_pipeline.py`, `backend/agents/persist_mcp_trace.py`, `backend/agents/`
- Contains: orchestration input construction, status transitions, `output_payload_json` persistence, `meta_json.ai_agents` enrichment, prompt registry lookups in `backend/agents/prompt_registry.py`, and optional LLM agent calls through `backend/services/recorded_chat_completion_service.py`.
- Depends on: `edgar_project/orchestration/agent.py`, `backend/services/run_step_service.py`, `backend/services/tool_call_service.py`, `backend/services/artifact_service.py`, `backend/llm/factory.py`
- Used by: synchronous `POST /v1/runs/{run_id}/execute` and the worker path in `backend/worker/loop.py`
- Purpose: Run the adaptive investigation loop — hypotheses, experiment selection from intermediate results, evidence updates, critique, typed termination, and an evidence-linked conclusion.
- Location: `agentic/agent/`, `agentic/domain/`, `agentic/experiments/`, `agentic/adapters/`, `agentic/evaluation/`
- Contains: the ten-component loop in `agentic/agent/loop.py` and `components.py`, budgets and safety caps in `agentic/agent/budget.py`, the instrumentation seam in `agentic/agent/observer.py`, resume/replay/diff in `agentic/agent/{store,replay,diff}.py`, typed entities in `agentic/domain/`, the deterministic experiment registry in `agentic/experiments/`, and dataset adapters (EDGAR, tabular, in-memory) in `agentic/adapters/`.
- Depends on: nothing in `backend/` or `edgar_project/` — the package is standalone and offline-safe. `agentic/domain` has no SQLAlchemy dependency; `agentic/` imports no structlog, OpenTelemetry, or prometheus.
- Used by: `backend/services/agentic_investigation_execution_service.py` (the single wiring point, which also injects `backend/observability/agent_observer.py`), `backend/services/investigation_replay_service.py`, and the offline agency suite in `agentic/evaluation/`
- Purpose: Persist investigation state and expose it read-only, owner-scoped.
- Location: `backend/models/investigation.py`, `backend/models/investigation_entities.py`, `backend/repositories/investigation_repository.py`, `backend/services/investigation_store.py`, `backend/services/investigation_create_service.py`, `backend/api/routes/investigations.py`
- Contains: the storage mapping for `InvestigationState` (hypotheses, evidence, experiments, decisions, critiques, conclusion), creation from a user-supplied dataset in `investigation_create_service.py`, and EDGAR panel materialization in `backend/services/edgar_panel_materializer.py`.
- Depends on: `agentic/domain` for the typed entities it serializes; additive reversible Alembic migrations
- Used by: `/v1/investigations` routes, the platform MCP server, and the frontend investigation surfaces under `frontend/src/app/projects/[projectId]/investigations/`
- Purpose: Expose the platform itself over MCP — commission an investigation, read its hypotheses and evidence, fetch the artifacts behind them.
- Location: `backend/mcp/`
- Contains: 9 tools and 2 resources in `backend/mcp/server.py`, the HTTP client in `backend/mcp/client.py`, and the two trust models (stdio env token vs. per-request bearer) in `backend/mcp/auth.py`.
- Depends on: the `/v1` API over HTTP — it is a client, not a second implementation, so auth, owner scoping, and 404-for-unauthorized are inherited rather than reimplemented. Shares `ToolResponseEnvelope` with the EDGAR server.
- Used by: external MCP clients over stdio (`python -m backend.mcp`) or streamable-HTTP
- Purpose: Validate orchestration requests, pick a plan template, hand planning to execution, and emit a typed `OrchestrationOutput`.
- Location: `edgar_project/orchestration/`
- Contains: coordinator `edgar_project/orchestration/agent.py`, pure planner `edgar_project/orchestration/planner.py`, executor `edgar_project/orchestration/executor.py`, handoff contract `edgar_project/orchestration/execution_contract.py`, mutable runtime state `edgar_project/orchestration/state.py`, and public wire schemas in `edgar_project/orchestration/schemas.py`.
- Depends on: `edgar_project/mcp/tools.py` from the executor only; the planner intentionally avoids `src/*` and network dependencies.
- Used by: `edgar_project/cli.py`, `backend/agents/traceable_analysis_pipeline.py`, tests under `tests/orchestration/`, and the compatibility wrapper `orchestration/agent.py`
- Purpose: Present the Phase 1 pipeline as deterministic tools and stdio MCP endpoints.
- Location: `edgar_project/mcp/`
- Contains: tool contracts in `edgar_project/mcp/schemas.py`, thin adapters in `edgar_project/mcp/adapters.py`, tool implementations in `edgar_project/mcp/tools.py`, stdio server in `edgar_project/mcp/server.py`, and local JSON CLI in `edgar_project/mcp/cli.py`.
- Depends on: `src/*`, `config.py`, repo-root path helpers, and data directories under `data/`
- Used by: `edgar_project/orchestration/executor.py`, external MCP clients, the evaluation mocks in `edgar_project/evaluation/orchestration_mocks.py`, and standalone MCP CLI usage
- Purpose: Fetch SEC data, normalize it, compute features and signals, detect anomalies, and write tabular/report artifacts.
- Location: `src/`, `config.py`, `main.py`
- Contains: data acquisition in `src/data_fetch.py`, panel building in `src/normalization.py`, features in `src/features.py`, anomaly detection in `src/anomaly.py`, peer and trend signals in `src/peer_signals.py` and `src/trend_breaks.py`, findings/report composition in `src/findings.py` and `src/report.py`, and orchestration/writers in `src/pipeline_runner.py`.
- Depends on: repo-root configuration in `config.py` and filesystem outputs under `data/raw/`, `data/processed/`, and `data/artifacts/`
- Used by: `main.py`, `edgar_project/mcp/adapters.py`, validation tooling in `src/manual_validation.py`, and the evaluation harness
- Purpose: Execute queued runs in the background, reclaim stale leases, and retry transient failures.
- Location: `backend/worker/`, `backend/services/run_queue_service.py`, `backend/services/run_lifecycle_service.py`, `backend/models/run_execution_job.py`
- Contains: worker entrypoint `backend/worker/__main__.py`, polling/finalization loop `backend/worker/loop.py`, queue row creation in `backend/services/run_queue_service.py`, retry/cancel logic in `backend/services/run_lifecycle_service.py`, and queue persistence in `backend/repositories/run_execution_job_repository.py`.
- Depends on: the same execution service as the synchronous path, plus DB-backed lease state.
- Used by: `POST /v1/runs` when `enqueue_execution=true`, `POST /v1/runs/{run_id}/retry`, and the Compose `worker` service in `docker-compose.yml`
- Purpose: Run deterministic benchmark suites against fixtures or mocked orchestration flows.
- Location: `edgar_project/evaluation/`, `edgar_project/evaluation/scripts/`, `edgar_project/evaluation/fixtures/`
- Contains: the runner in `edgar_project/evaluation/runner.py`, benchmark/result schemas in `edgar_project/evaluation/schemas.py`, artifact/orchestration checks, golden regression helpers, and suite definitions under `edgar_project/evaluation/benchmarks/`.
- Depends on: `src/*` for fixture-based execution and `edgar_project/orchestration/agent.py` for orchestration-mocked cases.
- Used by: `python3 -m edgar_project.cli evaluate`, `python3 -m edgar_project.cli demo --fixtures`, and tests
- Purpose: Provide object storage, structured logging, tracing, metrics, and request correlation.
- Location: `backend/storage/`, `backend/observability/`
- Contains: local object-store wiring in `backend/storage/factory.py` and `backend/storage/local.py`, artifact URI reading in `backend/storage/resolver.py`, request middleware in `backend/observability/middleware.py`, and structlog/OpenTelemetry setup in `backend/observability/logging.py` and `backend/observability/tracing.py`.
- Depends on: `backend/config/settings.py`
- Used by: API startup, worker startup, artifact delivery, and persisted traceability flows
## Data Flow
- Persistent product state lives in SQLAlchemy tables modeled by `backend/models/analysis_run.py`, `backend/models/run_step.py`, `backend/models/tool_call.py`, `backend/models/model_call.py`, `backend/models/artifact.py`, `backend/models/project.py`, and `backend/models/run_execution_job.py`.
- In-process orchestration state lives in `edgar_project/orchestration/state.py` as `OrchestrationRunState`; it is the executor’s scratch state and is converted back into `OrchestrationOutput`.
- Frontend transient state stays local to React components such as `frontend/src/components/chat-shell/chat-shell.tsx`; durable UI state is reloaded from backend resources instead of mirrored in a client store.
## Key Abstractions
- Purpose: Represent one persisted execution attempt and its lifecycle.
- Examples: `backend/models/analysis_run.py`, `backend/services/analysis_run_service.py`, `backend/schemas/analysis_run.py`
- Pattern: A parent row owns child `RunStep`, `ToolCall`, `Artifact`, `ModelCall`, and `RunExecutionJob` records; routes surface compact views through `backend/schemas/api_phase_a.py`.
- Purpose: Separate planned/executed step state from run-level outcome.
- Examples: `backend/models/run_step.py`, `backend/services/run_step_service.py`, `backend/agents/persist_mcp_trace.py`
- Pattern: Every visible execution phase becomes a `RunStep`; executed MCP steps also get a one-to-one `ToolCall`, while critic/report phases stay as LLM-flavored `RunStep` rows with rich `meta_json`.
- Purpose: Freeze the planner-to-executor boundary so execution can move out-of-process later without changing semantics.
- Examples: `edgar_project/orchestration/execution_contract.py`, `edgar_project/orchestration/state.py`, `edgar_project/orchestration/schemas.py`
- Pattern: `Planner` returns `PlanningOutcome`; `AnalysisAgent` converts it into `ExecutionRequest`; `Executor` returns `OrchestrationOutput`.
- Purpose: Normalize tool success, no-data, and error responses.
- Examples: `edgar_project/mcp/schemas.py`, `edgar_project/mcp/tools.py`, `edgar_project/orchestration/executor.py`
- Pattern: Tool functions never expose raw exceptions across the orchestration boundary; they return `ToolResponseEnvelope` with `status`, `message`, `data`, `artifacts`, and `errors`.
- Purpose: Carry agent summaries and UI-facing audit slices without requiring the frontend to parse full prompts or envelopes.
- Examples: `backend/agents/traceable_analysis_pipeline.py`, `backend/schemas/run_transparency.py`, `frontend/src/lib/ai-agents-meta.ts`, `frontend/src/lib/orchestration-output.ts`
- Pattern: backend writes compact data into `analysis_run.meta_json["ai_agents"]` and `analysis_run.output_payload_json`; frontend parsing helpers derive typed UI models from those fields.
- Purpose: Decouple artifact bytes from DB rows and HTTP delivery.
- Examples: `backend/models/artifact.py`, `backend/services/artifact_service.py`, `backend/storage/local.py`, `backend/api/routes/artifacts.py`
- Pattern: pipeline files are ingested into an object store and referenced by `storage_uri`; HTTP handlers stream bytes or bounded previews without exposing raw filesystem paths to the browser.
## Entry Points
- Location: `backend/main.py`
- Triggers: `uvicorn backend.main:app`, Compose `api` service, test clients
- Responsibilities: configure logging/tracing, ensure storage/database prerequisites, mount `ObservabilityMiddleware`, and register `/health`, `/metrics`, and `/v1/*` routers
- Location: `backend/worker/__main__.py`
- Triggers: `python -m backend.worker`, Compose `worker` service
- Responsibilities: configure observability, report LLM readiness, optionally expose worker metrics, and start the DB-backed polling loop in `backend/worker/loop.py`
- Location: `frontend/src/app/layout.tsx`
- Triggers: `next dev`, `next build`, `next start`
- Responsibilities: load the current user server-side, render the global shell, and hand off per-route work to `page.tsx`, `layout.tsx`, and `route.ts` files under `frontend/src/app/`
- Location: `edgar_project/cli.py`
- Triggers: `python3 -m edgar_project.cli run`, `demo`, `evaluate`
- Responsibilities: normalize CLI arguments, run orchestration or benchmark flows, and print digests or JSON
- Location: `edgar_project/mcp/server.py`
- Triggers: `python -m edgar_project.mcp.server` or `python -m edgar_project.mcp server`
- Responsibilities: expose the deterministic EDGAR *computation* as MCP tools with validated arguments and JSON envelopes
- Location: `backend/mcp/server.py`
- Triggers: `python -m backend.mcp` (stdio) or `python -m backend.mcp --transport streamable-http`
- Responsibilities: expose the *platform* as MCP tools and resources by calling `/v1` as the current caller; stdio uses `EDGAR_MCP_TOKEN`, hosted HTTP resolves each request's bearer header and never falls back to the environment token
- Location: `backend/maintenance/retention.py`
- Triggers: `python -m backend.maintenance.retention` (supports `--dry-run`)
- Responsibilities: compact run payloads, redact model payloads, and clean artifact blobs per the configured retention windows
- Location: `agentic/evaluation/__main__.py`
- Triggers: `python -m agentic.evaluation`
- Responsibilities: run the tiered agency benchmark against baselines and emit the scoreboard
- Location: `main.py`
- Triggers: `python3 main.py`
- Responsibilities: run the Phase 1 pipeline directly against `config.DEFAULT_TICKERS` and write artifacts without the backend persistence shell
- Location: `orchestration/agent.py`
- Triggers: `python -m orchestration.agent`
- Responsibilities: provide a thin developer-facing wrapper around `edgar_project.orchestration`
## Error Handling
- FastAPI routes such as `backend/api/routes/runs.py` and `backend/api/routes/artifacts.py` translate service errors into `HTTPException` responses; ownership checks in `backend/api/access_checks.py` deliberately return `404` for both missing and unauthorized resources.
- Service-layer transition rules live in `backend/services/analysis_run_service.py`, `backend/services/run_lifecycle_service.py`, `backend/services/run_step_service.py`, and `backend/services/tool_call_service.py`; invalid state changes raise typed exceptions instead of silently mutating rows.
- MCP tools in `edgar_project/mcp/tools.py` wrap validation, SEC request, file, and internal failures into `ToolResponseEnvelope` responses with structured `errors[]`.
- Orchestration aggregates typed warnings/errors into `OrchestrationOutput` in `edgar_project/orchestration/executor.py` rather than relying on logs alone.
- Worker execution in `backend/worker/loop.py` distinguishes terminal failures, transient failures, cancellations, and stale-lease recovery before deciding whether to requeue a job.
## Cross-Cutting Concerns
<!-- GSD:architecture-end -->
