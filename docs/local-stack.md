# Local full stack (API, worker, web, Postgres)

Concise runbook for **Docker Compose** (recommended) and **manual** processes. Settings use env prefix `EDGAR_BACKEND_` (see `backend/config/settings.py`).

## Database defaults (Compose vs manual)

**Recommended / documented default:** **Postgres**, as in `docker-compose.yml` (`EDGAR_BACKEND_DATABASE_URL` points at the `db` service). Use this for the full stack, CI-style compose smoke, and anything you treat as a “real” environment.

**Convenience default (no Docker):** If `EDGAR_BACKEND_DATABASE_URL` is **unset**, `backend/config/settings.py` falls back to a **SQLite file** at `data/backend.db`. That keeps local `pytest` and quick `uvicorn` runs working without Postgres. On startup the API and worker log a **`database_backend_sqlite`** warning so it is obvious you are not on the Compose default.

**Strict production:** Set **`EDGAR_BACKEND_ALLOW_SQLITE=false`** so a SQLite URL is rejected; use a Postgres URL only.

**Do not** mix “API on SQLite” with “worker on Postgres” for the same logical environment — both processes must use the same `EDGAR_BACKEND_DATABASE_URL`.

## Prerequisites

- **Compose:** Docker Compose **v2.20+** (`service_completed_successfully` for migrations).
- **Manual backend:** Python 3.12+, `pip install -r requirements.txt -r requirements-backend.txt`, repo root on `PYTHONPATH`.
- **Manual frontend:** Node 22+ (see `frontend/package.json`).

## Quick start (Compose)

From the **repository root**:

```bash
cp .env.example .env
# Set EDGAR_BACKEND_JWT_SECRET, EDGAR_BACKEND_OPS_API_TOKEN,
# and EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN in .env.
docker compose up --build
```

Optional wrapper (same thing):

```bash
./scripts/stack up
```

- **API:** http://127.0.0.1:8000 — e.g. `GET /v1/health`
- **Web:** http://127.0.0.1:3000

Stop and remove containers (keeps named volumes `pgdata` and `artifacts`):

```bash
docker compose down
# or: ./scripts/stack down
```

Reset DB + artifact blobs (destructive):

```bash
docker compose down -v
```

## Startup order (Compose)

1. **Postgres** (`db`) — healthy before anything else.
2. **migrate** — one-shot `alembic upgrade head`, then exits (`restart: "no"`). Do not scale this service; a second migrate job could race (Alembic generally serializes on the DB, but one-shot is the supported pattern).
3. **api** + **worker** — start only after **migrate exits successfully** (no API/worker traffic against an unmigrated schema).
4. **web** — starts after **api** passes `/v1/health` (same Docker network: `API_URL=http://api:8000`).

See inline comments in [`docker-compose.yml`](../docker-compose.yml).

## Migrations

**Compose:** handled by the `migrate` service; no separate step.

**Manual** (repo root, DB reachable):

```bash
export PYTHONPATH=.
export EDGAR_BACKEND_DATABASE_URL='postgresql+psycopg2://USER:PASS@HOST:5432/DB'   # or sqlite URL
alembic upgrade head
```

Alembic reads the URL from settings (`alembic/env.py` → `get_settings().database_url`). The URL in `alembic.ini` is only a placeholder.

**New DB:** `upgrade head` applies the full chain. **Existing DB:** same command applies pending revisions only.

## Environment setup

| Context | What to do |
|--------|------------|
| **Compose** | Copy [`.env.example`](../.env.example) to `.env` in the repo root before `docker compose up`. Set `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_OPS_API_TOKEN`, and `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`; the compose file fails fast if they are missing. Leave `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false` unless you explicitly want self-service sign-up. |
| **Manual API/worker** | Export `EDGAR_BACKEND_DATABASE_URL`, `EDGAR_BACKEND_JWT_SECRET` (≥32 chars if `EDGAR_BACKEND_DEBUG=false`), `EDGAR_BACKEND_OPS_API_TOKEN`, `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN`, and `EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT` (see below). |
| **Manual frontend** | `frontend/.env.local`: `API_URL=http://127.0.0.1:8000` (server-side only; see `frontend/.env.example`). |

Never commit real `.env` / `.env.local` files.

## Manual run (no Docker)

Use when you want hot reload or a debugger against a local DB.

**1. Database** — run Postgres yourself, or use the default **SQLite** file (`data/backend.db`) by leaving `EDGAR_BACKEND_DATABASE_URL` unset (see `backend/config/settings.py` defaults).

**2. Migrations** — `alembic upgrade head` as above.

**3. API** (repo root):

```bash
export PYTHONPATH=.
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**4. Worker** (separate terminal, repo root):

```bash
export PYTHONPATH=.
python -m backend.worker
```

**Worker queue:** each claim sets a **lease** (`lease_expires_at`). If a job stays `running` but the lease is **expired or missing** (crash, bug, or legacy row), the next poll **reclaims** it like a stale lease so the queue does not stick forever.

**5. Frontend** (`frontend/`):

```bash
cp .env.example .env.local   # set API_URL to your API origin
npm install
npm run dev
```

The browser talks to **Next**; Next calls the API using `API_URL` on the server.

## Artifact storage

- **Backend** stores blob paths as `local:` URIs under a single filesystem root: **`EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT`** (`backend/storage`, `open_reader`).
- **Compose:** `api` and **worker** mount the same named Docker volume **`artifacts`** at `/var/lib/edgar/artifacts`. The worker writes blobs; the API serves `GET /v1/artifacts/.../content`. Both must see the **same** directory (or volume).
- **Run workspaces:** `api` and **worker** also mount the shared named Docker volume **`run_workspaces`** at `/var/lib/edgar/run_workspaces`, and `EDGAR_BACKEND_RUN_WORKSPACE_ROOT` points there. Both processes must see the same run-workspace root or persisted runs will not resolve their own outputs correctly.
- **Manual dev:** artifact blobs still default to repo `data/artifact_storage/` (created on API startup). Durable run workspaces default to repo `data/runs/`; use the same run-workspace root for every API and worker process on that machine.
- **Optional remote storage:** set `EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND=s3` plus the `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_*` vars in `.env` to point the API and worker at one external **S3-compatible** object store. The app still serves artifact bytes through `/v1/artifacts/*`; clients do not talk to the bucket directly.
- **Still not in this stack:** MinIO or another bundled object store. Compose only passes through external S3-compatible settings when you opt in.

### Optional remote artifact storage

To keep the default local filesystem store, do nothing beyond the standard `artifacts` volume setup above.

To opt into one remote S3-compatible backend, add these vars to `.env` before `docker compose up` or `docker compose up -d --force-recreate api worker`:

```bash
EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND=s3
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET=your-artifact-bucket
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_REGION=us-east-1
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_PREFIX=
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ENDPOINT_URL=
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ACCESS_KEY_ID=
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY=
EDGAR_BACKEND_ARTIFACT_STORAGE_S3_FORCE_PATH_STYLE=false
```

Notes:

- Existing `local:` artifacts remain readable in a deployment configured for S3; rollout is mixed-read, not bulk migration.
- `storage_uri` values remain logical app-owned locators such as `local:...` or `s3:...`; they are not raw bucket or object identifiers.
- This stack still does not add MinIO. Point the settings at an external S3-compatible service if you need remote blob storage.

## Retention maintenance

Retention is an explicit operator workflow, not hidden cleanup during normal API or worker traffic.

Configure these env vars under the `EDGAR_BACKEND_` prefix:

- `EDGAR_BACKEND_RETENTION_RUN_PAYLOAD_DAYS` - age cutoff for trimming persisted analysis-run payload JSON; `0` disables this tier.
- `EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS` - age cutoff for redacting raw model request/response payload JSON; `0` disables this tier.
- `EDGAR_BACKEND_RETENTION_ARTIFACT_BLOB_DAYS` - age cutoff for pruning stored artifact blobs while keeping the artifact row plus tombstone metadata; `0` disables this tier.
- `EDGAR_BACKEND_RETENTION_BATCH_SIZE` - max rows/blobs handled per maintenance batch.

Use the maintenance entrypoint from the repo root after migrations are current and the target database is reachable:

```bash
python -m backend.maintenance.retention --dry-run --json
python -m backend.maintenance.retention --apply --json
```

Dry-run reports candidate counts without mutation. Apply mode compacts run payloads, redacts model payloads, and prunes eligible artifact blobs by deleting the stored object and setting `artifacts.blob_deleted_at` so later content requests return an explicit retention-expired response instead of looking like accidental storage loss.

## Verification (after `docker compose up -d`)

**Automated** (requires curl, docker CLI, Python 3 on the host):

```bash
./scripts/smoke-compose.sh
# or: ./scripts/stack smoke
```

Checks: Postgres `pg_isready`, `alembic current` in `api`, `GET /v1/health` with `database.ok`, `GET /` on the web port, worker container running. Override ports if needed: `API_PORT=8080 WEB_PORT=3001 ./scripts/smoke-compose.sh`.

**Manual checklist**

| Step | Command / expectation |
|------|------------------------|
| DB up | `docker compose exec db pg_isready -U edgar -d edgar` |
| Migrations | `docker compose exec api sh -c 'cd /app && alembic current'` shows a revision id |
| Backend | `curl -sS http://127.0.0.1:8000/v1/health` → JSON with `"database":{"ok":true}` |
| Ops auth | `curl -sS http://127.0.0.1:8000/metrics -H "Authorization: Bearer $EDGAR_BACKEND_OPS_API_TOKEN"` returns Prometheus text; `curl -sS http://127.0.0.1:8000/v1/worker/health -H "Authorization: Bearer $EDGAR_BACKEND_OPS_API_TOKEN"` returns JSON |
| Worker | `docker compose ps worker` → `running` |
| Frontend | `curl -sS -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/` → `200` |

## Bootstrap the first admin

With the stack running and `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN` set in `.env`:

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/auth/bootstrap" \
  -H "Content-Type: application/json" \
  -H "X-EDGAR-Bootstrap-Token: $EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN" \
  -d '{"email":"admin@local.dev","password":"your-password-here","display_name":"Local Admin"}'
```

Registration is disabled by default, so use this bootstrap flow for the first operator account unless you intentionally set `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=true`.

## Scripts

| Script | Purpose |
|--------|---------|
| [`scripts/stack`](../scripts/stack) | `up` / `down` (pass-through to docker compose); `smoke` → [`smoke-compose.sh`](smoke-compose.sh). |
| [`scripts/smoke-compose.sh`](../scripts/smoke-compose.sh) | Host-side smoke checks (stack already running). |

## See also

- [`docs/auth-api.md`](auth-api.md) — bootstrap admin, JWT auth, registration posture, and ops-token routes.
- [`docker-compose.yml`](../docker-compose.yml), [`Dockerfile`](../Dockerfile), [`frontend/Dockerfile`](../frontend/Dockerfile).
