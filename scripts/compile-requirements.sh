#!/usr/bin/env bash
# Regenerate the pinned lockfiles from the loose requirements*.txt sources.
#
# The loose files (requirements.txt, requirements-backend.txt, requirements-dev.txt) are the
# human-edited source of truth. This script resolves them inside the deploy image
# (python:3.12-slim-bookworm) so the pins match production exactly, and writes:
#   - requirements.lock      (runtime: used by the Dockerfile)
#   - requirements-dev.lock  (runtime + dev/CI tooling: used by CI)
#
# Run after editing any requirements*.txt, then commit the updated .lock files.
set -euo pipefail
cd "$(dirname "$0")/.."

docker run --rm -v "$PWD":/w -w /w python:3.12-slim-bookworm bash -c '
  set -e
  pip install -q uv
  uv pip compile -q requirements.txt requirements-backend.txt -o requirements.lock
  uv pip compile -q requirements-dev.txt -o requirements-dev.lock
'

echo "Regenerated requirements.lock and requirements-dev.lock"
echo "Review the diff and commit the updated lockfiles."
