#!/usr/bin/env python3
"""Export the API's OpenAPI schema, or fail when the committed copy has drifted.

The schema is generated from the live FastAPI app, so it is always *derivable* — but that
is exactly why it is easy to forget. Without a committed artifact there is nothing to review
in a diff, nothing for a client generator to consume without booting the stack, and no signal
when a route change alters the public contract.

Committing ``docs/api/openapi.json`` makes an API change visible in code review: adding a
route, renaming a field, or changing a status code shows up as a diff on the contract rather
than only inside a handler.

Usage::

    python3 scripts/export-openapi.py            # write docs/api/openapi.json
    python3 scripts/export-openapi.py --check    # fail if the committed copy is stale (CI)

The app is built with fixed settings so the schema depends only on the code, never on the
environment the exporter happens to run in.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
OUTPUT = REPO_ROOT / "docs" / "api" / "openapi.json"

#: Fixed so two machines produce byte-identical output. These only need to satisfy the
#: settings validators; the schema does not embed them.
_DETERMINISTIC_ENV = {
    "EDGAR_BACKEND_JWT_SECRET": "openapi-export-placeholder-secret-value",
    "EDGAR_BACKEND_DATABASE_URL": "sqlite:///./openapi-export.db",
    "EDGAR_BACKEND_ALLOW_SQLITE": "true",
    # Required whenever open registration is off (the default), or Settings refuses to build.
    "EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN": "openapi-export-placeholder-bootstrap",
    "EDGAR_BACKEND_OPS_API_TOKEN": "openapi-export-placeholder-ops",
}


def build_schema() -> dict:
    """Build the app's schema hermetically.

    ``Settings`` reads ``.env`` relative to the working directory, so this runs from a temp
    directory: a developer's local ``.env`` must not be able to influence a contract that CI
    then checks against a machine that has none. (That asymmetry is exactly how this script
    first passed locally and failed in CI.)
    """
    sys.path.insert(0, str(REPO_ROOT))
    for key, value in _DETERMINISTIC_ENV.items():
        os.environ.setdefault(key, value)

    previous_cwd = Path.cwd()
    with tempfile.TemporaryDirectory() as sandbox:
        os.chdir(sandbox)
        try:
            from backend.config.settings import get_settings
            from backend.main import create_app

            get_settings.cache_clear()  # type: ignore[attr-defined]
            return create_app().openapi()
        finally:
            os.chdir(previous_cwd)


def render(schema: dict) -> str:
    # sort_keys so the diff reflects real contract changes, not dict ordering.
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed schema differs from the current app.",
    )
    args = parser.parse_args(argv)

    current = render(build_schema())

    if not args.check:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(current)
        paths = len(json.loads(current)["paths"])
        print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)} ({paths} paths)")
        return 0

    if not OUTPUT.is_file():
        print(
            f"FAIL: {OUTPUT.relative_to(REPO_ROOT)} is missing.\n"
            "      Run: python3 scripts/export-openapi.py",
            file=sys.stderr,
        )
        return 1

    committed = OUTPUT.read_text()
    if committed == current:
        print(f"OK: {OUTPUT.relative_to(REPO_ROOT)} matches the current API.")
        return 0

    print(
        f"FAIL: {OUTPUT.relative_to(REPO_ROOT)} is stale — the API changed but the committed\n"
        "      contract did not. Regenerate and commit it so the change is reviewable:\n"
        "          python3 scripts/export-openapi.py",
        file=sys.stderr,
    )
    _report_path_delta(json.loads(committed), json.loads(current))
    return 1


def _report_path_delta(committed: dict, current: dict) -> None:
    """Name added/removed routes, so the failure is actionable without a diff tool."""
    was, now = set(committed.get("paths", {})), set(current.get("paths", {}))
    for label, paths in (("added", now - was), ("removed", was - now)):
        for path in sorted(paths):
            print(f"      {label}: {path}", file=sys.stderr)
    if was == now:
        print("      (no route added or removed — a schema or response shape changed)", file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
