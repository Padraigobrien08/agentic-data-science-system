# HTTP authentication (secure defaults)

## How it works (high level)

1. **Users** are rows in `users` with a **bcrypt** hash (`cost` 12) in `hashed_password`.
2. **No server-side sessions** for the API: after `POST /v1/auth/login`, clients send **`Authorization: Bearer <jwt>`** on every protected call.
3. **JWT** is **HS256**, short-lived (see `EDGAR_BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES`). The payload identifies the user; the server validates the signature and loads the user from the DB.
4. **Authorization** for data is **owner-based**: projects belong to a user; runs belong to a project; artifacts are reachable only if linked to runs (or equivalent) in a project you own. Missing or foreign resources return **404** so IDs are not enumerable across tenants.
5. **Web UI (Next.js)** stores the access token in an **HttpOnly** cookie and attaches `Authorization: Bearer` on server-side requests to the FastAPI backend (`API_URL`). Browser code does not read the token.

Unauthenticated calls to protected routes get **401** with `WWW-Authenticate: Bearer`. Invalid or expired tokens get **401** with detail `Invalid or expired token`.

## Creating the first local admin

Prerequisites: backend running with:

- `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN` set to a non-empty operator secret
- `EDGAR_BACKEND_JWT_SECRET` set to your real signing secret
- `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false` (the default secure posture)

**1. Bootstrap the first admin** (email + password; password must be **10–72** characters):

```bash
BOOTSTRAP_TOKEN="<your-bootstrap-token>"
curl -sS -X POST "http://127.0.0.1:8000/v1/auth/bootstrap" \
  -H "Content-Type: application/json" \
  -H "X-EDGAR-Bootstrap-Token: $BOOTSTRAP_TOKEN" \
  -d '{"email":"admin@local.dev","password":"your-password-here","display_name":"Local Admin"}'
```

This route succeeds only once. After the first admin exists, `POST /v1/auth/bootstrap` returns **409** with `Bootstrap already completed`.

**2. Log in** (returns `access_token` and `expires_in`):

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@local.dev","password":"your-password-here"}'
```

**3. Call the API** (example: list your projects):

```bash
TOKEN="<paste access_token>"
curl -sS "http://127.0.0.1:8000/v1/projects" \
  -H "Authorization: Bearer $TOKEN"
```

`POST /v1/auth/register` is closed by default. When `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false`, the route returns **403** with `Registration is disabled`. Enable it explicitly only if you want self-service sign-up in that environment.

## Open registration (explicit opt-in)

If you choose to enable self-service registration:

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@local.dev","password":"your-password-here","display_name":"Local"}'
```

The Next.js app uses **`/login`** (email/password form) which performs the same login against the backend and sets the session cookie.

## Ops token for `/metrics` and `/v1/worker/health`

`/metrics` and `/v1/worker/health` are protected with the dedicated bearer token from `EDGAR_BACKEND_OPS_API_TOKEN`, not the end-user JWT.

```bash
OPS_TOKEN="<your-ops-token>"
curl -sS "http://127.0.0.1:8000/metrics" \
  -H "Authorization: Bearer $OPS_TOKEN"

curl -sS "http://127.0.0.1:8000/v1/worker/health" \
  -H "Authorization: Bearer $OPS_TOKEN"
```

## Which routes require auth

| Auth | Method | Path | Notes |
|------|--------|------|--------|
| No | GET | `/health`, `/v1/health` | Liveness + DB check |
| No | GET | `/v1/ready` | Readiness |
| No | POST | `/v1/auth/bootstrap` | Requires `X-EDGAR-Bootstrap-Token`; first admin only |
| No | POST | `/v1/auth/register` | **403** unless open registration is explicitly enabled |
| No | POST | `/v1/auth/login` | Returns JWT |
| Ops bearer | GET | `/metrics`, `/v1/worker/health` | Requires `Authorization: Bearer <EDGAR_BACKEND_OPS_API_TOKEN>` |
| Yes | GET | `/v1/auth/me` | Current user profile, including `is_admin` |
| Yes | GET, POST | `/v1/projects`, `/v1/projects/{id}` | List/create/get **own** projects only |
| Yes | GET, POST | `/v1/runs` | List (optional `project_id`) / create run in **own** project |
| Yes | GET | `/v1/runs/{run_id}` | Run detail (own run only → else **404**); `include_payloads=true` is admin-only |
| Yes | GET | `/v1/runs/{run_id}/status` | |
| Yes | GET | `/v1/runs/{run_id}/steps` | `include_payloads=true` is admin-only |
| Yes | GET | `/v1/runs/{run_id}/artifacts` | |
| Yes | GET | `/v1/runs/{run_id}/model-calls` | `include_payloads=true` is admin-only |
| Yes | POST | `/v1/runs/{run_id}/execute` | |
| Yes | POST | `/v1/runs/{run_id}/cancel` | |
| Yes | POST | `/v1/runs/{run_id}/retry` | |
| Yes | GET | `/v1/artifacts/{id}` | Metadata (own artifact only → else **404**); `include_meta=true` is admin-only |
| Yes | GET | `/v1/artifacts/{id}/content` | Stream bytes |
| Yes | GET | `/v1/artifacts/{id}/preview` | Text/JSON preview (**415** if not previewable) |

Routers for `projects`, `runs`, and `artifacts` are mounted with a shared dependency on the active user (`backend/api/router.py`). `POST /v1/runs` sets `initiated_by_user_id` from the token; clients must not rely on spoofing ownership via the body.

Raw `include_payloads=true` and `include_meta=true` expansions are deliberately not part of the normal owner contract. Those larger debug views require an authenticated admin user and return **403** for non-admin owners.

## Environment variables and secrets

All backend settings use the prefix **`EDGAR_BACKEND_`** (see `backend/config/settings.py`).

| Variable | Role |
|----------|------|
| `EDGAR_BACKEND_JWT_SECRET` | Required HMAC key for signing access tokens. Must be **≥ 32 characters** when `EDGAR_BACKEND_DEBUG=false`, and the built-in dev secret is rejected unless `EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT=true`. |
| `EDGAR_BACKEND_JWT_ALGORITHM` | Default `HS256`. |
| `EDGAR_BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default `720`). |
| `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION` | Default `false`; set `true` only when you intentionally want self-service registration. |
| `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN` | Required operator secret for `POST /v1/auth/bootstrap`. |
| `EDGAR_BACKEND_OPS_API_TOKEN` | Required bearer token for `/metrics` and `/v1/worker/health`. |
| `EDGAR_BACKEND_ALLOW_INSECURE_DEV_JWT` | Default `false`; set `true` only for explicit local development with the built-in secret. |
| `EDGAR_BACKEND_DEBUG` | Default `false`; when `false`, weak JWT secret length is rejected at startup. |

**Frontend** (Next.js): `API_URL` (server-side base URL for the backend), and optional `NEXT_PUBLIC_DEFAULT_PROJECT_ID` for a dev shortcut link on the home page. The session cookie name is defined in the frontend as `edgar_api_session` (JWT value, HttpOnly).

Do not commit real `EDGAR_BACKEND_JWT_SECRET`, `EDGAR_BACKEND_OPS_API_TOKEN`, or `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN` values; use `.env` locally and a secret manager in deployment.

## Automated tests

Focused API tests live in **`tests/test_auth_api.py`**:

1. Registration + login + `GET /v1/auth/me`
2. Authenticated access to projects and runs list
3. Unauthenticated requests to protected paths → **401**
4. Invalid JWT → **401**
5. Project/run listing and detail scoped to owner; foreign project → **404** for run list; foreign run detail → **404**
6. Duplicate registration → **409**; bad login → **401**
7. Artifact metadata, **content**, and **preview** denied for another user (**404**)

Shared helper: **`tests/api_auth.py`** (`register_project_and_headers`) for tests that need a user, JWT headers, and a project.
