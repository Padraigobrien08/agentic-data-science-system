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
API_BASE="http://127.0.0.1:${API_PORT}"
WEB_BASE="http://127.0.0.1:${WEB_PORT}"
SMOKE_WORKER_TIMEOUT="${SMOKE_WORKER_TIMEOUT:-300}"

die() { echo "smoke: $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
need_cmd curl
need_cmd docker
need_cmd python3

pg_user="${POSTGRES_USER:-edgar}"
pg_db="${POSTGRES_DB:-edgar}"

api_id="$(docker compose ps -q api 2>/dev/null || true)"
[[ -n "$api_id" ]] || die "no api container — start the stack: docker compose up -d (or ./scripts/stack up -d)"

api_running="$(docker inspect -f '{{.State.Running}}' "$api_id" 2>/dev/null || echo false)"
[[ "$api_running" == "true" ]] || die "api container exists but is not running"

echo "==> Postgres (pg_isready in db container)"
docker compose exec -T db pg_isready -U "$pg_user" -d "$pg_db" >/dev/null \
  || die "Postgres not accepting connections"

echo "==> Alembic revision (api container)"
docker compose exec -T api sh -c 'cd /app && alembic current' \
  || die "alembic current failed"

echo "==> Backend GET ${API_BASE}/v1/health"
health_json="$(curl -sfS "${API_BASE}/v1/health")" || die "API health request failed"
python3 -c 'import json,sys; d=json.loads(sys.argv[1]); assert d.get("database",{}).get("ok") is True, d' "$health_json" \
  || die "API health JSON missing database.ok=true"

echo "==> Worker queue snapshot GET ${API_BASE}/v1/worker/health"
curl -sfS "${API_BASE}/v1/worker/health" | python3 -m json.tool >/dev/null \
  || die "worker health request failed"

echo "==> Frontend GET ${WEB_BASE}/"
code="$(curl -sfS -o /dev/null -w "%{http_code}" "${WEB_BASE}/")" || die "frontend request failed"
[[ "$code" == "200" ]] || die "frontend HTTP $code (expected 200)"

echo "==> Worker container running"
worker_id="$(docker compose ps -q worker 2>/dev/null || true)"
[[ -n "$worker_id" ]] || die "no worker container"
worker_running="$(docker inspect -f '{{.State.Running}}' "$worker_id" 2>/dev/null || echo false)"
[[ "$worker_running" == "true" ]] || die "worker container not running"

echo "==> Enqueue test run + wait for terminal status (timeout ${SMOKE_WORKER_TIMEOUT}s)"
API_BASE="$API_BASE" SMOKE_WORKER_TIMEOUT="$SMOKE_WORKER_TIMEOUT" python3 <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.request

api = os.environ["API_BASE"].rstrip("/")
timeout = int(os.environ.get("SMOKE_WORKER_TIMEOUT", "300"))
password = "Smokepass12!"  # min 10 chars for register


def jreq(method: str, path: str, payload: dict | None = None, headers: dict | None = None) -> dict:
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
        err = e.read().decode() or str(e)
        print(f"smoke: HTTP {e.code} {path}: {err}", file=sys.stderr)
        raise SystemExit(1) from e


email = f"smoke-{int(time.time())}@example.com"
jreq("POST", "/v1/auth/register", {"email": email, "password": password})
token = jreq("POST", "/v1/auth/login", {"email": email, "password": password})["access_token"]
auth = {"Authorization": f"Bearer {token}"}
project_id = jreq("POST", "/v1/projects", {"name": "smoke-compose"}, headers=auth)["id"]
run_body = {
    "project_id": str(project_id),
    "orchestration_goal_text": "smoke",
    "input_payload_json": {"tickers": ["AAPL"], "analysis_goal": "smoke compose health check"},
    "enqueue_execution": True,
}
run_id = jreq("POST", "/v1/runs", run_body, headers=auth)["id"]

deadline = time.time() + timeout
while time.time() < deadline:
    st = jreq("GET", f"/v1/runs/{run_id}/status", headers=auth)
    if st.get("is_terminal"):
        print(f"smoke: run {run_id} terminal status={st.get('status')!r}")
        sys.exit(0)
    time.sleep(3)

print(f"smoke: timeout waiting for terminal run {run_id}", file=sys.stderr)
sys.exit(1)
PY

echo "smoke: OK"
