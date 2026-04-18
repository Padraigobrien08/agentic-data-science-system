#!/usr/bin/env bash
# Post-up checks for the Docker Compose stack (repo root).
# Usage: from repo root after `docker compose up -d`, run:
#   ./scripts/smoke-compose.sh
# Optional: API_PORT=8080 WEB_PORT=3001 SMOKE_WORKER_TIMEOUT=600 ./scripts/smoke-compose.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
API_BASE="${API_BASE:-http://127.0.0.1:${API_PORT}}"
WEB_BASE="${WEB_BASE:-http://127.0.0.1:${WEB_PORT}}"
SMOKE_WORKER_TIMEOUT="${SMOKE_WORKER_TIMEOUT:-120}"

die() { echo "smoke: $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
require_env() { [[ -n "${!1:-}" ]] || die "missing required env: $1"; }

need_cmd curl
need_cmd docker
need_cmd python3
require_env EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN
require_env EDGAR_BACKEND_OPS_API_TOKEN
require_env EDGAR_SMOKE_ADMIN_EMAIL
require_env EDGAR_SMOKE_ADMIN_PASSWORD

pg_user="${POSTGRES_USER:-edgar}"
pg_db="${POSTGRES_DB:-edgar}"

api_id="$(docker compose ps -q api 2>/dev/null || true)"
[[ -n "$api_id" ]] || die "no api container — start the stack: docker compose up -d (or ./scripts/stack up -d)"

api_running="$(docker inspect -f '{{.State.Running}}' "$api_id" 2>/dev/null || echo false)"
[[ "$api_running" == "true" ]] || die "api container exists but is not running"

echo "==> Postgres (pg_isready in db container)"
docker compose exec -T db pg_isready -U "$pg_user" -d "$pg_db" >/dev/null \
  || die "Postgres not accepting connections"

echo "==> Migrate container completed successfully"
migrate_id="$(docker compose ps -a -q migrate 2>/dev/null || true)"
[[ -n "$migrate_id" ]] || die "no migrate container"
migrate_state="$(docker inspect -f '{{.State.Status}}' "$migrate_id" 2>/dev/null || echo unknown)"
migrate_exit_code="$(docker inspect -f '{{.State.ExitCode}}' "$migrate_id" 2>/dev/null || echo 1)"
[[ "$migrate_state" == "exited" && "$migrate_exit_code" == "0" ]] \
  || die "migrate container did not complete successfully (status=${migrate_state} exit=${migrate_exit_code})"

echo "==> Alembic revision (api container)"
docker compose exec -T api sh -c 'cd /app && alembic current' \
  || die "alembic current failed"

echo "==> Backend GET ${API_BASE}/v1/health"
health_json="$(curl -sfS "${API_BASE}/v1/health")" || die "API health request failed"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d.get("database",{}).get("ok") is True, d' "$health_json" \
  || die "API health JSON missing database.ok=true"

echo "==> Ops metrics GET ${API_BASE}/metrics"
curl -sfS -o /dev/null \
  -H "Authorization: Bearer ${EDGAR_BACKEND_OPS_API_TOKEN}" \
  "${API_BASE}/metrics" \
  || die "metrics request failed"

echo "==> Worker queue snapshot GET ${API_BASE}/v1/worker/health"
worker_health_json="$(
  curl -sfS \
    -H "Authorization: Bearer ${EDGAR_BACKEND_OPS_API_TOKEN}" \
    "${API_BASE}/v1/worker/health"
)" || die "worker health request failed"
printf '%s' "$worker_health_json" | python3 -m json.tool >/dev/null \
  || die "worker health request failed"

echo "==> Frontend GET ${WEB_BASE}/"
code="$(curl -sfS -o /dev/null -w "%{http_code}" "${WEB_BASE}/")" || die "frontend request failed"
[[ "$code" == "200" ]] || die "frontend HTTP $code (expected 200)"

echo "==> Worker container running"
worker_id="$(docker compose ps -q worker 2>/dev/null || true)"
[[ -n "$worker_id" ]] || die "no worker container"
worker_running="$(docker inspect -f '{{.State.Running}}' "$worker_id" 2>/dev/null || echo false)"
[[ "$worker_running" == "true" ]] || die "worker container not running"

echo "==> Bootstrap admin + login + authenticated project list"
API_BASE="$API_BASE" \
SMOKE_WORKER_TIMEOUT="$SMOKE_WORKER_TIMEOUT" \
EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN="$EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN" \
EDGAR_SMOKE_ADMIN_EMAIL="$EDGAR_SMOKE_ADMIN_EMAIL" \
EDGAR_SMOKE_ADMIN_PASSWORD="$EDGAR_SMOKE_ADMIN_PASSWORD" \
python3 <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.request

api = os.environ["API_BASE"].rstrip("/")
bootstrap_token = os.environ["EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN"]
email = os.environ["EDGAR_SMOKE_ADMIN_EMAIL"]
password = os.environ["EDGAR_SMOKE_ADMIN_PASSWORD"]
smoke_worker_timeout = float(os.environ["SMOKE_WORKER_TIMEOUT"])
goal = "find unusual financial changes"


class RequestFailure(RuntimeError):
    def __init__(self, status: int, path: str, body: str) -> None:
        super().__init__(f"HTTP {status} {path}: {body or 'empty response body'}")
        self.status = status
        self.path = path
        self.body = body


def jreq(
    method: str,
    path: str,
    payload: dict | None = None,
    headers: dict | None = None,
) -> dict | list[object]:
    h = dict(headers or {})
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(f"{api}{path}", data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read()
            if not body:
                return {}
            return json.loads(body.decode())
    except urllib.error.HTTPError as e:
        raise RequestFailure(e.code, path, e.read().decode() or str(e)) from e


def ensure_no_permission_denied(label: str, payload: object) -> None:
    if "Permission denied" in json.dumps(payload, sort_keys=True):
        print(f"smoke: {label} surfaced Permission denied", file=sys.stderr)
        raise SystemExit(1)


try:
    jreq(
        "POST",
        "/v1/auth/bootstrap",
        {
            "email": email,
            "password": password,
            "display_name": "Smoke Admin",
        },
        headers={"X-EDGAR-Bootstrap-Token": bootstrap_token},
    )
    print("smoke: bootstrap admin ok")
except RequestFailure as exc:
    if exc.status == 409 and "Bootstrap already completed" in exc.body:
        print("smoke: bootstrap already completed; continuing with login")
    else:
        print(f"smoke: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc

login = jreq(
    "POST",
    "/v1/auth/login",
    {"email": email, "password": password},
)
token = login["access_token"]
projects = jreq(
    "GET",
    "/v1/projects",
    headers={"Authorization": f"Bearer {token}"},
)
if not isinstance(projects, list):
    print("smoke: /v1/projects did not return a list", file=sys.stderr)
    raise SystemExit(1)

print(f"smoke: authenticated project list ok ({len(projects)} projects)")

auth_headers = {"Authorization": f"Bearer {token}"}
project = next((p for p in projects if p.get("slug") == "smoke-runtime"), None)
if project is None:
    project = jreq(
        "POST",
        "/v1/projects",
        {
            "name": "Smoke Runtime",
            "slug": "smoke-runtime",
            "tickers": ["MSFT"],
        },
        headers=auth_headers,
    )
elif "MSFT" not in (project.get("tickers") or []):
    project = jreq(
        "PATCH",
        f"/v1/projects/{project['id']}",
        {"tickers": ["MSFT"]},
        headers=auth_headers,
    )

project_id = project["id"]
print(f"smoke: using project {project_id}")

sync_run = jreq(
    "POST",
    "/v1/runs",
    {
        "project_id": project_id,
        "orchestration_goal_text": goal,
        "input_payload_json": {
            "tickers": ["MSFT"],
            "analysis_goal": goal,
        },
    },
    headers=auth_headers,
)
ensure_no_permission_denied("sync run create", sync_run)

sync_execute = jreq(
    "POST",
    f"/v1/runs/{sync_run['id']}/execute",
    {},
    headers=auth_headers,
)
ensure_no_permission_denied("sync run execute", sync_execute)
if sync_execute.get("db_status") == "error":
    print(f"smoke: sync run errored: {sync_execute}", file=sys.stderr)
    raise SystemExit(1)

sync_status = jreq(
    "GET",
    f"/v1/runs/{sync_run['id']}/status",
    headers=auth_headers,
)
ensure_no_permission_denied("sync run status", sync_status)
if sync_status.get("status") == "error":
    print(f"smoke: sync run status errored: {sync_status}", file=sys.stderr)
    raise SystemExit(1)

queued_run = jreq(
    "POST",
    "/v1/runs",
    {
        "project_id": project_id,
        "orchestration_goal_text": goal,
        "input_payload_json": {
            "tickers": ["MSFT"],
            "analysis_goal": goal,
        },
        "enqueue_execution": True,
    },
    headers=auth_headers,
)
ensure_no_permission_denied("queued run create", queued_run)

deadline = time.monotonic() + smoke_worker_timeout
while True:
    queued_status = jreq(
        "GET",
        f"/v1/runs/{queued_run['id']}/status",
        headers=auth_headers,
    )
    ensure_no_permission_denied("queued run status", queued_status)
    run_status = queued_status.get("status")
    latest_job = queued_status.get("latest_execution_job") or {}
    latest_job_status = latest_job.get("status")

    if run_status == "error":
        print(f"smoke: queued run errored: {queued_status}", file=sys.stderr)
        raise SystemExit(1)
    if latest_job_status in {"failed", "cancelled"}:
        print(f"smoke: queued worker job failed before claim succeeded: {queued_status}", file=sys.stderr)
        raise SystemExit(1)
    if run_status not in {"queued", "pending"} or latest_job_status not in {None, "pending"}:
        print(
            f"smoke: queued run left initial state ({run_status=}, {latest_job_status=})"
        )
        break
    if time.monotonic() >= deadline:
        print("smoke: queued run never left initial queued/pending state", file=sys.stderr)
        raise SystemExit(1)
    time.sleep(2)
PY

echo "smoke: OK"
