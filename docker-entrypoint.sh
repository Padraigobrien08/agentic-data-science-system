#!/bin/sh
# Fix ownership on mounted artifact volume (named volumes are often root-owned).
# Then run the main process as appuser (uid 1000).
set -e
ART="${EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT:-/var/lib/edgar/artifacts}"
RUNS="${EDGAR_BACKEND_RUN_WORKSPACE_ROOT:-/var/lib/edgar/run_workspaces}"
# Manual validation is a human-maintained record, so it lives on a writable volume
# rather than in the image. src/report.py resolves it at PROJECT_ROOT/validation.
VALIDATION="/app/validation"
mkdir -p "$ART"
mkdir -p "$RUNS"
mkdir -p "$VALIDATION"
if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser "$ART" 2>/dev/null || true
  chown -R appuser:appuser "$RUNS" 2>/dev/null || true
  chown -R appuser:appuser "$VALIDATION" 2>/dev/null || true
fi

# Seed the header-only CSV via the canonical helper, so the column list cannot drift
# from VALIDATION_COLUMNS. Idempotent: it only writes when the file is absent or empty.
# Without this the report reports "file not found at validation/manual_validation.csv",
# leaking an internal path and implying a broken install rather than the true state,
# which is that no one has verified the figures yet.
if [ "$(id -u)" = "0" ]; then
  runuser -u appuser -- python -c \
    "from src.manual_validation import ensure_validation_csv; ensure_validation_csv()" \
    2>/dev/null || true
  exec runuser -u appuser -- "$@"
fi
python -c "from src.manual_validation import ensure_validation_csv; ensure_validation_csv()" \
  2>/dev/null || true
exec "$@"
