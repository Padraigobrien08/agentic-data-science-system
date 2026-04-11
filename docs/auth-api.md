# HTTP authentication (baseline)

## How it works (high level)

1. **Users** are rows in `users` with a **bcrypt** hash (`cost` 12) in `hashed_password`.
2. **No server-side sessions** for the API: after `POST /v1/auth/login`, clients send **`Authorization: Bearer <jwt>`** on every protected call.
3. **JWT** is **HS256**, short-lived (see `EDGAR_BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES`). The payload identifies the user; the server validates the signature and loads the user from the DB.
4. **Authorization** for data is **owner-based**: projects belong to a user; runs belong to a project; artifacts are reachable only if linked to runs (or equivalent) in a project you own. Missing or foreign resources return **404** so IDs are not enumerable across tenants.
5. **Web UI (Next.js)** stores the access token in an **HttpOnly** cookie and attaches `Authorization: Bearer` on server-side requests to the FastAPI backend (`API_URL`). Browser code does not read the token.

Unauthenticated calls to protected routes get **401** with `WWW-Authenticate: Bearer`. Invalid or expired tokens get **401** with detail `Invalid or expired token`.

## Creating a local user

Prerequisites: backend running with defaults (`EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION` defaults to **true**).

**1. Register** (email + password; password must be **10–72** characters):

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@local.dev","password":"your-password-here","display_name":"Local"}'
```

**2. Log in** (returns `access_token` and `expires_in`):

```bash
curl -sS -X POST "http://127.0.0.1:8000/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"you@local.dev","password":"your-password-here"}'
```

**3. Call the API** (example: list your projects):

```bash
TOKEN="<paste access_token>"
curl -sS "http://127.0.0.1:8000/v1/projects" \
  -H "Authorization: Bearer $TOKEN"
```

If registration is disabled (`EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false`), `POST /v1/auth/register` returns **403**. In that case create users through your own admin path or temporarily re-enable registration.

The Next.js app uses **`/login`** (email/password form) which performs the same login against the backend and sets the session cookie.

## Which routes require auth

| Auth | Method | Path | Notes |
|------|--------|------|--------|
| No | GET | `/health`, `/v1/health` | Liveness + DB check |
| No | GET | `/v1/ready` | Readiness |
| No | POST | `/v1/auth/register` | **403** if open registration off |
| No | POST | `/v1/auth/login` | Returns JWT |
| Yes | GET | `/v1/auth/me` | Current user profile |
| Yes | GET, POST | `/v1/projects`, `/v1/projects/{id}` | List/create/get **own** projects only |
| Yes | GET, POST | `/v1/runs` | List (optional `project_id`) / create run in **own** project |
| Yes | GET | `/v1/runs/{run_id}` | Run detail (own run only → else **404**) |
| Yes | GET | `/v1/runs/{run_id}/status` | |
| Yes | GET | `/v1/runs/{run_id}/steps` | |
| Yes | GET | `/v1/runs/{run_id}/artifacts` | |
| Yes | POST | `/v1/runs/{run_id}/execute` | |
| Yes | POST | `/v1/runs/{run_id}/cancel` | |
| Yes | POST | `/v1/runs/{run_id}/retry` | |
| Yes | GET | `/v1/artifacts/{id}` | Metadata (own artifact only → else **404**) |
| Yes | GET | `/v1/artifacts/{id}/content` | Stream bytes |
| Yes | GET | `/v1/artifacts/{id}/preview` | Text/JSON preview (**415** if not previewable) |

Routers for `projects`, `runs`, and `artifacts` are mounted with a shared dependency on the active user (`backend/api/router.py`). `POST /v1/runs` sets `initiated_by_user_id` from the token; clients must not rely on spoofing ownership via the body.

## Environment variables and secrets

All backend settings use the prefix **`EDGAR_BACKEND_`** (see `backend/config/settings.py`).

| Variable | Role |
|----------|------|
| `EDGAR_BACKEND_JWT_SECRET` | **Required in production**: HMAC key for signing access tokens. Must be **≥ 32 characters** when `EDGAR_BACKEND_DEBUG=false`. |
| `EDGAR_BACKEND_JWT_ALGORITHM` | Default `HS256`. |
| `EDGAR_BACKEND_ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime (default `720`). |
| `EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION` | Default `true`; set `false` to return **403** on `POST /v1/auth/register`. |
| `EDGAR_BACKEND_DEBUG` | Default `false`; when `false`, weak JWT secret length is rejected at startup. |

**Frontend** (Next.js): `API_URL` (server-side base URL for the backend), and optional `NEXT_PUBLIC_DEFAULT_PROJECT_ID` for a dev shortcut link on the home page. The session cookie name is defined in the frontend as `edgar_api_session` (JWT value, HttpOnly).

Do not commit real `EDGAR_BACKEND_JWT_SECRET` values; use `.env` locally and a secret manager in deployment.

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
