#!/bin/sh
# Fix ownership on mounted artifact volume (named volumes are often root-owned).
# Then run the main process as appuser (uid 1000).
set -e
ART="${EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT:-/var/lib/edgar/artifacts}"
mkdir -p "$ART"
if [ "$(id -u)" = "0" ]; then
  chown -R appuser:appuser "$ART" 2>/dev/null || true
  exec runuser -u appuser -- "$@"
fi
exec "$@"
