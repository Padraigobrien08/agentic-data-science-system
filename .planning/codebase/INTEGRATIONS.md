# External Integrations

**Analysis Date:** 2026-04-15

## APIs & External Services

**Financial Data APIs:**
- SEC EDGAR - Primary external data source for ticker resolution, submissions JSON, and XBRL company facts.
  - SDK/Client: `requests` sessions in `src/data_fetch.py`, wrapped by MCP tools in `edgar_project/mcp/tools.py` and orchestration in `edgar_project/orchestration/executor.py`.
  - Auth: No API key detected. The integration relies on a descriptive SEC `User-Agent` string defined in `config.py`.
  - Endpoints surfaced in code: `https://www.sec.gov/files/company_tickers.json`, `https://data.sec.gov/submissions/CIK{cik10}.json`, and `https://data.sec.gov/api/xbrl/companyfacts/CIK{cik10}.json` in `config.py`.

**LLM Providers:**
- OpenAI Chat Completions - Optional provider for the agent-style intent, planning, critic, and report phases under `backend/agents/` and `backend/llm/`.
  - SDK/Client: `openai` via `backend/llm/openai_provider.py`.
  - Auth: `EDGAR_BACKEND_OPENAI_API_KEY` or `OPENAI_API_KEY`, plus `EDGAR_BACKEND_LLM_PROVIDER=openai`; optional base URL comes from the `openai_base_url` setting in `backend/config/settings.py`.
  - Default posture: disabled (`llm_provider="off"`) in `backend/config/settings.py` and `backend/llm/factory.py`.

**Internal Service Interfaces:**
- FastAPI REST API - Primary application boundary exposed from `backend/main.py` and route modules in `backend/api/routes/`.
  - SDK/Client: Native `fetch` from Next.js server components, route handlers, and server actions in `frontend/src/lib/api/client.ts`, `frontend/src/actions/auth.ts`, and `frontend/src/app/api/artifacts/[artifactId]/*/route.ts`.
  - Auth: Bearer JWT forwarded from the `edgar_api_session` HttpOnly cookie in `frontend/src/lib/auth/backend-auth.ts`.
- MCP stdio server - Developer-facing tool interface for Cursor, Claude Desktop, or MCP Inspector.
  - SDK/Client: `FastMCP` server in `edgar_project/mcp/server.py`, mirrored by the local JSON CLI in `edgar_project/mcp/cli.py`.
  - Auth: None detected; the transport is local stdio, not an authenticated HTTP service.
- Python CLIs - Local operator interfaces for the full pipeline and evaluation flows.
  - SDK/Client: `python -m edgar_project.cli` in `edgar_project/cli.py`, `python -m edgar_project.mcp.cli` in `edgar_project/mcp/cli.py`, and `python main.py` in `main.py`.
  - Auth: Local process execution only.

## Data Storage

**Databases:**
- PostgreSQL - Documented default database for the full stack and Compose-based environments.
  - Connection: `EDGAR_BACKEND_DATABASE_URL`, read in `backend/config/settings.py` and consumed by `backend/db/session.py`.
  - Client: SQLAlchemy ORM plus `psycopg2-binary`, with migrations through `alembic/env.py`.
- SQLite - Local-development fallback when `EDGAR_BACKEND_DATABASE_URL` is unset.
  - Connection: implicit fallback to `data/backend.db` from `backend/config/settings.py`.
  - Client: SQLAlchemy sync engine in `backend/db/session.py`.

**File Storage:**
- Local filesystem only - Artifact blobs are stored behind `local:` URIs in `backend/storage/local.py` and resolved through `backend/storage/resolver.py`.
  - Storage root: `EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT`, defaulting to `data/artifact_storage/` in `backend/config/settings.py`.
  - Shared runtime requirement: API and worker must point at the same filesystem root or Docker volume, per `docs/local-stack.md`.
- Pipeline output directories - Analytical CSV/Markdown outputs are written under `data/processed/`, `data/artifacts/`, and `data/evaluation/`, as described in `config.py`, `README.md`, and `data/README.md`.
- SEC raw cache - Downloaded SEC JSON is cached under `data/raw/` by `src/data_fetch.py`.

**Caching:**
- No dedicated cache service is detected.
- Filesystem caching is built into the SEC fetch layer: `src/data_fetch.py` reuses `data/raw/company_tickers.json` and per-ticker raw JSON files under `data/raw/{TICKER}/`.

## Authentication & Identity

**Auth Provider:**
- Custom JWT auth.
  - Implementation: Registration/login/current-user routes live in `backend/api/routes/auth.py`.
  - Token format: HS256 JWTs created in `backend/auth/tokens.py`.
  - Password storage: bcrypt hashes produced by `backend/security/passwords.py`.
  - API transport: `Authorization: Bearer <token>` enforced by `backend/api/auth_deps.py`.
  - Frontend session bridge: Next.js stores the JWT in the `edgar_api_session` HttpOnly cookie in `frontend/src/actions/auth.ts` and forwards it server-side through `frontend/src/lib/auth/backend-auth.ts`.
  - Authorization model: owner-scoped access to projects, runs, and artifacts in `backend/api/access_checks.py` and the route handlers under `backend/api/routes/`.

## Monitoring & Observability

**Error Tracking:**
- None detected for third-party error tracking. No Sentry, Rollbar, Bugsnag, or equivalent SDK/config is present.

**Logs:**
- Structured application logs use `structlog` in `backend/observability/logging.py`.
- Request, run, and trace context are injected through `backend/observability/middleware.py` and `backend/observability/context.py`.
- MCP tool metrics/log hooks are registered from `backend/observability/install.py` into `edgar_project/orchestration/telemetry_callbacks.py`.

**Metrics:**
- Prometheus scraping is supported.
  - API scrape endpoint: `GET /metrics` in `backend/api/routes/metrics.py`.
  - Worker scrape endpoint: optional standalone HTTP server started by `backend/worker/__main__.py` when `EDGAR_BACKEND_WORKER_METRICS_PORT > 0`.
  - Metric definitions: `backend/observability/metrics.py`.

**Tracing:**
- OpenTelemetry W3C trace propagation is implemented in `backend/observability/tracing.py`.
  - Export path: OTLP HTTP via `OTEL_EXPORTER_OTLP_ENDPOINT` / `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT`, or console mode via `OTEL_TRACES_EXPORTER=console`.
  - Worker continuation: trace carriers are serialized across queued jobs, then restored in worker execution, as described in `backend/observability/tracing.py`.

## CI/CD & Deployment

**Hosting:**
- Docker Compose local/self-hosted stack is the documented deployment model in `docs/local-stack.md`.
- Service topology described in docs and Compose comments: `db`, `migrate`, `api`, `worker`, and `web`, with backend image in `Dockerfile` and frontend image in `frontend/Dockerfile`.
- No cloud deployment platform, serverless adapter, or IaC-managed hosting target is detected.

**CI Pipeline:**
- GitHub Actions CI in `.github/workflows/ci.yml`.
  - Backend job: installs `requirements-dev.txt` and runs `python -m pytest tests/ -q --tb=short`.
  - Frontend job: runs `npm ci`, `npm run lint`, and `npm run build` in `frontend/`.
- Optional Compose smoke workflow in `.github/workflows/compose-smoke.yml`.
  - Scope: builds/starts the API dependency chain and checks `GET /v1/health`.

## Environment Configuration

**Required env vars:**
- Backend core:
  - `EDGAR_BACKEND_DATABASE_URL` - DB connection for API, migrations, and worker in `backend/config/settings.py` and `alembic/env.py`.
  - `EDGAR_BACKEND_JWT_SECRET` - JWT signing secret used by `backend/auth/tokens.py`.
  - `EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT` - Shared artifact filesystem root used by `backend/storage/local.py`.
  - `EDGAR_BACKEND_ALLOW_SQLITE` - Production posture guard enforced by `backend/config/settings.py`.
  - `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION` - Registration gate checked in `backend/api/routes/auth.py`.
- Optional LLM and agent controls:
  - `EDGAR_BACKEND_LLM_PROVIDER`, `EDGAR_BACKEND_OPENAI_API_KEY`, `OPENAI_API_KEY`, and the `openai_base_url` / timeout settings in `backend/config/settings.py`.
  - `EDGAR_BACKEND_AGENT_*MODEL`, `EDGAR_BACKEND_AGENT_*PROMPT_VERSION`, `EDGAR_BACKEND_AGENT_CONTEXT_*`, and `EDGAR_BACKEND_AGENT_LLM_PRICING_JSON` from `backend/config/settings.py`.
- Observability:
  - `EDGAR_BACKEND_WORKER_METRICS_PORT` from `backend/worker/__main__.py`.
  - `OTEL_SERVICE_NAME`, `OTEL_TRACES_EXPORTER`, `EDGAR_BACKEND_OTEL_TRACES_EXPORTER`, `OTEL_EXPORTER_OTLP_ENDPOINT`, and `OTEL_EXPORTER_OTLP_TRACES_ENDPOINT` from `backend/observability/tracing.py`.
- Frontend:
  - `API_URL` required by `frontend/src/lib/api/config.ts`.
  - `NEXT_PUBLIC_DEFAULT_PROJECT_ID` is optional, used by `frontend/src/lib/landing-project.ts`.
- Compose helper variables referenced by smoke tooling:
  - `POSTGRES_USER` and `POSTGRES_DB` in `scripts/smoke-compose.sh`.

**Secrets location:**
- Local backend secrets are expected in repo-root `.env`, as configured by `backend/config/settings.py` and documented in `docs/local-stack.md`.
- Local frontend runtime config is expected in `frontend/.env.local`, as documented in `docs/local-stack.md`.
- Example templates exist at `.env.example` and `frontend/.env.example`.
- Production guidance in `docs/auth-api.md` says to keep real secrets out of git and use a secret manager.

## Webhooks & Callbacks

**Incoming:**
- None detected. Route definitions in `backend/api/routes/` expose REST endpoints for health, auth, projects, runs, artifacts, and metrics; no webhook or callback receiver endpoints are present.
- Developer-facing callback-style interface is local stdio MCP, not an HTTP webhook, in `edgar_project/mcp/server.py`.

**Outgoing:**
- SEC EDGAR HTTPS requests originate from `src/data_fetch.py`.
- OpenAI HTTPS requests originate from `backend/llm/openai_provider.py` when `EDGAR_BACKEND_LLM_PROVIDER=openai`.
- OTLP exporter traffic can be emitted from `backend/observability/tracing.py` when OTLP env vars are configured.
- Internal server-to-server requests flow from Next.js to FastAPI through `API_URL` in `frontend/src/lib/api/client.ts`, `frontend/src/actions/auth.ts`, and `frontend/src/app/api/artifacts/[artifactId]/*/route.ts`.

---

*Integration audit: 2026-04-15*
