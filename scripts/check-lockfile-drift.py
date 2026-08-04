#!/usr/bin/env python3
"""Fail when the pinned lockfiles no longer satisfy the loose requirements.

The loose ``requirements*.txt`` files are the human-edited source of truth, but
``requirements.lock`` / ``requirements-dev.lock`` are what Docker and CI actually
install (see the Dockerfile and .github/workflows/ci.yml). Nothing keeps the two in
step automatically: dependabot raises floors in the loose files only, so a merged bump
leaves the lock stale until someone runs ``scripts/compile-requirements.sh``.

That drift is quiet and CI stays green, because CI installs the old pin. It bites
later, when the next person regenerates and silently picks up an untested version.
This check makes the drift loud at the point it is introduced.

Two failure modes are reported:

* **below floor** — a package is pinned lower than the floor the loose file declares,
  so the lock does not satisfy its own constraints.
* **missing** — a package was added to a loose file but never compiled into the lock,
  so it will not be installed at all.

Run locally with ``python3 scripts/check-lockfile-drift.py``; fix either by running
``scripts/compile-requirements.sh``.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import InvalidVersion, Version

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Which loose files each lockfile is compiled from (mirrors compile-requirements.sh).
_TARGETS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("requirements.lock", ("requirements.txt", "requirements-backend.txt")),
    (
        "requirements-dev.lock",
        ("requirements.txt", "requirements-backend.txt", "requirements-dev.txt"),
    ),
)

_PIN_RE = re.compile(r"^([A-Za-z0-9._-]+)\s*==\s*([^\s;#]+)")


def _declared_floors(sources: tuple[str, ...]) -> dict[str, tuple[str, str]]:
    """Map canonical package name -> (floor version, originating file).

    ``-r`` includes are ignored: every file they could pull in is already listed
    explicitly in _TARGETS, so following them would only double-count.
    """
    floors: dict[str, tuple[str, str]] = {}
    for source in sources:
        path = _REPO_ROOT / source
        if not path.exists():
            continue
        for raw in path.read_text().splitlines():
            line = raw.split("#", 1)[0].strip()
            if not line or line.startswith("-"):
                continue
            try:
                req = Requirement(line)
            except Exception:
                continue  # not a plain requirement (URL, editable, ...)
            if req.marker is not None and not req.marker.evaluate():
                continue  # not applicable to this interpreter
            lower = next(
                (
                    spec.version
                    for spec in req.specifier
                    if spec.operator in {">=", "==", "~="}
                ),
                None,
            )
            if lower is None:
                continue
            floors[canonicalize_name(req.name)] = (lower, source)
    return floors


def _locked_pins(lockfile: str) -> dict[str, str]:
    pins: dict[str, str] = {}
    path = _REPO_ROOT / lockfile
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        match = _PIN_RE.match(line)
        if match:
            pins.setdefault(canonicalize_name(match.group(1)), match.group(2))
    return pins


def main() -> int:
    problems: list[str] = []
    for lockfile, sources in _TARGETS:
        if not (_REPO_ROOT / lockfile).exists():
            problems.append(f"{lockfile}: missing entirely")
            continue
        floors = _declared_floors(sources)
        pins = _locked_pins(lockfile)
        for name, (floor, source) in sorted(floors.items()):
            pin = pins.get(name)
            if pin is None:
                problems.append(
                    f"{lockfile}: {name} is declared in {source} (>={floor}) "
                    f"but is not pinned in the lock — it will not be installed"
                )
                continue
            try:
                if Version(pin) < Version(floor):
                    problems.append(
                        f"{lockfile}: {name} is pinned at {pin} but {source} "
                        f"declares >={floor} — the lock does not satisfy its floor"
                    )
            except InvalidVersion:
                continue
        print(f"{lockfile}: checked {len(floors)} declared floors against {len(pins)} pins")

    if problems:
        print("\nLockfile drift detected:\n", file=sys.stderr)
        for problem in problems:
            print(f"  - {problem}", file=sys.stderr)
        print(
            "\nRegenerate with scripts/compile-requirements.sh, then commit the "
            "updated .lock files.",
            file=sys.stderr,
        )
        return 1

    print("OK: every declared floor is satisfied by the corresponding lockfile.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
