# Technology Stack

**Analysis Date:** 2026-04-15

## Languages

**Primary:**
- Python 3.12+ - Backend API, worker, orchestration, MCP server, evaluation tooling, and the Phase 1 EDGAR pipeline live in `backend/`, `edgar_project/`, `src/`, and `main.py`.
- TypeScript - The web app, server actions, route handlers, and frontend tests live in `frontend/src/`, with config in `frontend/next.config.ts`, `frontend/tsconfig.json`, and `frontend/vitest.config.ts`.

**Secondary:**
- SQL / migration DSL - Relational schema and migrations are maintained through `backend/models/` and `alembic/versions/`.
- Bash - Local stack wrappers and smoke checks live in `scripts/stack` and `scripts/smoke-compose.sh`.
- Dockerfile / Compose YAML - Container build and local deployment definitions live in `Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml`.
- Markdown / Jupyter - Operational docs and demo notebooks live in `docs/`, `README.md`, and `notebooks/demo_edgar_pipeline.ipynb`.

## Runtime

**Environment:**
- CPython 3.12 - The backend container uses `python:3.12-slim-bookworm` in `Dockerfile`; CI also installs Python 3.12 in `.github/workflows/ci.yml`.
- Node.js 22 for containerized frontend - `frontend/Dockerfile` uses `node:22-bookworm-slim`.
- Node.js 20 in CI - `.github/workflows/ci.yml` runs the frontend job with Node 20.
- Browser + Next.js server runtime - The App Router web UI runs from `frontend/src/app/`, with server-only API calls in `frontend/src/lib/api/` and `frontend/src/actions/`.

**Package Manager:**
- Python: `pip` (version not pinned) using `requirements.txt`, `requirements-backend.txt`, and `requirements-dev.txt`.
- Python lockfile: missing. Dependency resolution is requirements-based, not lockfile-based.
- Frontend: `npm` (version not pinned) using `frontend/package.json`.
- Lockfile: present at `frontend/package-lock.json`.
- Additional lockfile present: `frontend/pnpm-lock.yaml` exists, but CI, Docker, and docs all use `npm`, not `pnpm`.

## Frameworks

**Core:**
- FastAPI `>=0.115.0` - Main HTTP API in `backend/main.py`, with route modules in `backend/api/routes/`.
- SQLAlchemy `>=2.0.36` - ORM and session layer in `backend/db/session.py`, `backend/models/`, and repository/service code under `backend/repositories/` and `backend/services/`.
- Alembic `>=1.14.0` - Schema migrations configured in `alembic/env.py` with revision files in `alembic/versions/`.
- Pydantic 2 + `pydantic-settings` - Request/response schemas and env-driven settings in `backend/schemas/`, `edgar_project/*/schemas.py`, and `backend/config/settings.py`.
- Next.js `^15.1.0` - App Router frontend in `frontend/src/app/`, with build/runtime config in `frontend/next.config.ts`.
- React `^19.0.0` - UI component layer in `frontend/src/components/` and page composition in `frontend/src/app/`.
- FastMCP / MCP SDK `mcp>=1.0` - Stdio MCP server in `edgar_project/mcp/server.py` and local MCP CLI in `edgar_project/mcp/cli.py`.

**Testing:**
- `pytest>=8.0` - Backend and orchestration test suite under `tests/`, invoked in `.github/workflows/ci.yml`.
- Vitest `^2.1.9` - Frontend unit tests in `frontend/src/__tests__/` and `frontend/src/lib/__tests__/`, configured by `frontend/vitest.config.ts`.
- Testing Library + jsdom - Frontend component/runtime testing via `@testing-library/react`, `@testing-library/dom`, and `jsdom` from `frontend/package.json`.

**Build/Dev:**
- Uvicorn `>=0.30.0` - ASGI server for the FastAPI app, launched from `Dockerfile` and `docs/local-stack.md`.
- Docker Compose - Recommended full-stack orchestration documented in `docs/local-stack.md` and wrapped by `scripts/stack`.
- Tailwind CSS `^3.4.16` - Utility styling configured in `frontend/tailwind.config.ts` and used from `frontend/src/app/globals.css`.
- ESLint `^9.16.0` with `eslint-config-next` - Frontend linting from `frontend/.eslintrc.json` and `.github/workflows/ci.yml`.
- Turbopack - Local frontend development uses `next dev --turbopack` in `frontend/package.json`.

## Key Dependencies

**Critical:**
- `pandas>=2.0` - Core dataframe pipeline for normalization, features, reporting, and evaluation in files such as `src/anomaly.py`, `src/report.py`, and `edgar_project/evaluation/analytical_checks.py`.
- `numpy>=1.24` - Numerical computations in the anomaly and peer-signal layers, e.g. `src/anomaly.py` and `src/peer_signals.py`.
- `requests>=2.28` - External SEC HTTP access in `src/data_fetch.py` and error handling adapters in `edgar_project/mcp/adapters.py`.
- `openai>=1.40.0` - Optional LLM provider for intent, planning, critic, and report phases in `backend/llm/openai_provider.py` and `backend/llm/factory.py`.
- `PyJWT>=2.8.0` - HS256 JWT issue/verify logic in `backend/auth/tokens.py` and `backend/api/auth_deps.py`.
- `bcrypt>=4.1.0` - Password hashing and verification in `backend/security/passwords.py`.
- `react-markdown^10.1.0` - Markdown artifact rendering in `frontend/src/components/runs/markdown-report.tsx`.

**Infrastructure:**
- `psycopg2-binary>=2.9.9` - Postgres connectivity behind `EDGAR_BACKEND_DATABASE_URL`, used through SQLAlchemy in `backend/db/session.py`.
- `structlog>=24.4.0` - Structured JSON logging in `backend/observability/logging.py`, used by API, worker, and services such as `backend/services/edgar_pipeline_execution_service.py`.
- `prometheus-client>=0.21.0` - API and worker metrics in `backend/api/routes/metrics.py`, `backend/worker/__main__.py`, and `backend/observability/metrics.py`.
- `opentelemetry-api`, `opentelemetry-sdk`, and `opentelemetry-exporter-otlp-proto-http` - Trace propagation/export in `backend/observability/tracing.py` and executor tracing in `edgar_project/orchestration/executor.py`.
- `email-validator>=2.0.0` - Email field validation for auth schemas under `backend/schemas/auth.py` and `backend/schemas/user.py`.

## Configuration

**Environment:**
- Backend settings are centralized in `backend/config/settings.py` via `BaseSettings` with env prefix `EDGAR_BACKEND_` and repo-root env file support (`env_file=".env"`).
- Frontend server-side backend origin is read from `API_URL` in `frontend/src/lib/api/config.ts`.
- Optional public frontend shortcut config uses `NEXT_PUBLIC_DEFAULT_PROJECT_ID` in `frontend/src/lib/landing-project.ts`.
- OpenAI credentials can come from `EDGAR_BACKEND_OPENAI_API_KEY` or fallback `OPENAI_API_KEY`, as implemented in `backend/config/settings.py`.
- Local env files are present but were not read: repo-root `.env`, repo-root `.env.example`, and `frontend/.env.example`.
- High-value backend config knobs include `EDGAR_BACKEND_DATABASE_URL`, `EDGAR_BACKEND_ALLOW_SQLITE`, `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION`, `EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT`, `EDGAR_BACKEND_LLM_PROVIDER`, `EDGAR_BACKEND_WORKER_METRICS_PORT`, and the `EDGAR_BACKEND_AGENT_*` model/prompt/context fields declared in `backend/config/settings.py`.
- Observability config uses `OTEL_SERVICE_NAME`, `OTEL_TRACES_EXPORTER`, `EDGAR_BACKEND_OTEL_TRACES_EXPORTER`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` in `backend/observability/tracing.py`.

**Build:**
- Backend image build is defined in `Dockerfile`; frontend image build is defined in `frontend/Dockerfile`.
- Local multi-service startup is documented in `docs/local-stack.md` and represented in `docker-compose.yml`.
- Database migrations load runtime settings from `backend/config/settings.py` through `alembic/env.py`.
- Frontend build/runtime config lives in `frontend/next.config.ts`, `frontend/tailwind.config.ts`, `frontend/tsconfig.json`, and `frontend/.eslintrc.json`.
- CI build/test entrypoints live in `.github/workflows/ci.yml` and `.github/workflows/compose-smoke.yml`.

## Platform Requirements

**Development:**
- Python 3.12+ with `pip` and repo-root `PYTHONPATH=.` for backend CLI/API/worker flows, as documented in `README.md` and `docs/local-stack.md`.
- Node.js 22+ for local frontend development, per `docs/local-stack.md`; Node 20 is sufficient for CI in `.github/workflows/ci.yml`.
- Docker Compose v2.20+ for the documented full stack, per `docs/local-stack.md`.
- Writable local filesystem access to `data/`, `data/artifact_storage/`, and migration state under `alembic/`.

**Production:**
- The documented deployment target is a self-hosted container stack built from `Dockerfile`, `frontend/Dockerfile`, and `docker-compose.yml`.
- Backend production posture is Postgres-backed, with `EDGAR_BACKEND_ALLOW_SQLITE=false` recommended by `backend/config/settings.py` and `docs/local-stack.md`.
- A separate worker process is part of the supported runtime model, launched via `python -m backend.worker` or the Compose `worker` service described in `docs/local-stack.md`.
- Shared artifact storage is a filesystem path or Docker volume mounted into both API and worker processes, as described by `backend/storage/local.py` and `docs/local-stack.md`.
- No cloud-specific deployment target, Terraform, Kubernetes manifests, or managed-hosting adapter is detected in the repository.

---

*Stack analysis: 2026-04-15*
