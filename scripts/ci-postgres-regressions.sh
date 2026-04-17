#!/usr/bin/env bash
set -euo pipefail

if [[ -z "${EDGAR_TEST_POSTGRES_URL:-}" ]]; then
  echo "EDGAR_TEST_POSTGRES_URL must be set to a non-empty PostgreSQL SQLAlchemy URL." >&2
  exit 1
fi

export EDGAR_TEST_POSTGRES_URL

python3 -m pytest \
  tests/test_run_isolation_overlap.py \
  tests/test_worker_lease_heartbeat.py \
  tests/test_worker_job_lifecycle_postgres.py \
  -q \
  --tb=short
