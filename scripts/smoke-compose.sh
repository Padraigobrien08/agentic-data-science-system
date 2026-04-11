#!/usr/bin/env bash
# Post-up checks for the Docker Compose stack (repo root).
# Usage: from repo root after `docker compose up -d`, run:
#   ./scripts/smoke-compose.sh
# Optional: API_PORT=8080 WEB_PORT=3001 ./scripts/smoke-compose.sh

set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

API_PORT="${API_PORT:-8000}"
WEB_PORT="${WEB_PORT:-3000}"
API_BASE="http://127.0.0.1:${API_PORT}"
WEB_BASE="http://127.0.0.1:${WEB_PORT}"

die() { echo "smoke: $*" >&2; exit 1; }

need_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
need_cmd curl
need_cmd docker

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

echo "==> Frontend GET ${WEB_BASE}/"
code="$(curl -sfS -o /dev/null -w "%{http_code}" "${WEB_BASE}/")" || die "frontend request failed"
[[ "$code" == "200" ]] || die "frontend HTTP $code (expected 200)"

echo "==> Worker container running"
worker_id="$(docker compose ps -q worker 2>/dev/null || true)"
[[ -n "$worker_id" ]] || die "no worker container"
worker_running="$(docker inspect -f '{{.State.Running}}' "$worker_id" 2>/dev/null || echo false)"
[[ "$worker_running" == "true" ]] || die "worker container not running"

echo "smoke: OK"
