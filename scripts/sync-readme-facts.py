"""
Keep the README's numbers in step with the runs it is describing.

The README stated its figures by hand, and they drifted — as hand-copied figures do. At the
time of writing they claimed the flagship run cost $0.0101 over 11 model calls (the committed
capture says $0.0131 over 12), and the whole second example described a run with "twelve
evidence records, six experiments" that matched no published demo at all: it had been
re-recorded, the prose had not.

That matters more here than on most projects. The pitch is that every number traces back to
the computation that produced it, and the first numbers a reader meets are in the README.

So the prose makes the argument and this table carries the figures, generated from the same
committed export the product serves:

    python3 scripts/sync-readme-facts.py            # rewrite the block
    python3 scripts/sync-readme-facts.py --check    # fail if it is stale (CI)

Reads only committed files, so it needs no database and no network.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATIC_DIR = REPO_ROOT / "frontend" / "src" / "lib" / "demo-static"
README = REPO_ROOT / "README.md"

BEGIN = "<!-- BEGIN GENERATED: published-runs -->"
END = "<!-- END GENERATED: published-runs -->"

#: How the loop's own vocabulary reads in a sentence. The table shows both: the typed value is
#: what the API serves and what a reader can grep for, the gloss is what it means.
OUTCOME_GLOSS = {
    "supported": "every claim stood",
    "mixed": "one claim stood, one did not",
    "contradicted": "two claims could not both be true",
    "refuted": "the run disproved its own claims",
    "declined": "no claim survived the evidence",
    "unanswerable": "the data cannot answer this",
    "stopped": "cut off before deciding",
}


def _load(slug: str, suffix: str = "") -> dict:
    return json.loads((STATIC_DIR / f"{slug}{suffix}.json").read_text())


def _rows() -> list[dict]:
    index = json.loads((STATIC_DIR / "index.json").read_text())
    rows = []
    for summary in index:
        slug = summary["demo_slug"]
        detail = _load(slug)
        capture = _load(slug, ".capture")
        outcome = summary["outcome"]
        rows.append(
            {
                "slug": slug,
                "kind": outcome["kind"],
                "termination": outcome["termination_reason"] or "—",
                "experiments": len(detail["experiments"]),
                "evidence": len(detail["evidence"]),
                "artifacts": sum(len(x["artifacts"]) for x in detail["experiments"]),
                "linked": sum(1 for e in detail["evidence"] if e.get("experiment_result_id")),
                "model_calls": capture["totals"]["model_calls"],
                "cost": capture["totals"]["est_cost_usd"],
                "origin": (detail["datasets"] or [{}])[0].get("origin", "unknown"),
            }
        )
    return rows


def _test_counts() -> tuple[int, int]:
    """Backend and frontend test counts, collected rather than remembered."""
    backend = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/", "-q", "--collect-only"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    match = re.search(r"(\d+) tests? collected", backend.stdout)
    backend_count = int(match.group(1)) if match else 0

    frontend = subprocess.run(
        ["npm", "--prefix", "frontend", "test", "--", "--reporter=json", "--run"],
        cwd=REPO_ROOT, capture_output=True, text=True, check=False,
    )
    frontend_count = 0
    try:
        payload = json.loads(frontend.stdout[frontend.stdout.index("{"):])
        frontend_count = int(payload.get("numTotalTests") or 0)
    except (ValueError, KeyError, json.JSONDecodeError):
        pass
    return backend_count, frontend_count


def render(*, with_tests: bool = True) -> str:
    rows = _rows()
    lines = [
        BEGIN,
        "",
        "| Run | Outcome | Stopped because | Experiments | Evidence | Artifacts | Model calls | Cost | Data |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        gloss = OUTCOME_GLOSS.get(r["kind"], r["kind"])
        evidence = f"{r['evidence']}"
        if r["linked"] != r["evidence"]:
            # Say so rather than round it up: an unlinked evidence row is one a reader cannot
            # trace to the computation behind it, which is the guarantee this table exists for.
            evidence += f" ({r['linked']} linked)"
        lines.append(
            f"| [`{r['slug']}`](frontend/src/lib/demo-static/{r['slug']}.json) "
            f"| **{r['kind']}** — {gloss} | `{r['termination']}` "
            f"| {r['experiments']} | {evidence} | {r['artifacts']} "
            f"| {r['model_calls']} | ${r['cost']:.4f} | {r['origin']} |"
        )

    total = sum(r["cost"] for r in rows)
    linked = sum(r["linked"] for r in rows)
    evidence = sum(r["evidence"] for r in rows)
    lines += [
        "",
        f"{len(rows)} runs, ${total:.4f} of model spend, "
        f"{linked} of {evidence} evidence records linked to the experiment that produced them.",
    ]
    if with_tests:
        backend, frontend = _test_counts()
        if backend and frontend:
            lines.append(f"{backend:,} backend tests · {frontend} frontend tests.")
    lines += ["", END]
    return "\n".join(lines)


def _replace(text: str, block: str) -> str:
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.S)
    if not pattern.search(text):
        raise SystemExit(
            f"README.md has no generated block. Add these markers where the table belongs:\n"
            f"  {BEGIN}\n  {END}"
        )
    return pattern.sub(lambda _: block, text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if the block is stale.")
    args = parser.parse_args()

    current = README.read_text()
    # Test counts need a pytest collection and an npm run; skip them under --check so the CI
    # job stays cheap, and compare only the run figures, which is where drift actually happens.
    block = render(with_tests=not args.check)
    if args.check:
        existing = re.search(re.escape(BEGIN) + r"(.*?)" + re.escape(END), current, re.S)
        if existing is None:
            print("README.md has no generated published-runs block.", file=sys.stderr)
            return 1
        # Compare the table rows only; the trailing test counts are refreshed on demand.
        want = {line for line in block.splitlines() if line.startswith("| [`")}
        have = {line for line in existing.group(0).splitlines() if line.startswith("| [`")}
        if want != have:
            print("README.md is out of step with the committed demo export.", file=sys.stderr)
            for line in sorted(want - have):
                print(f"  expected: {line}", file=sys.stderr)
            for line in sorted(have - want):
                print(f"  found:    {line}", file=sys.stderr)
            print("\nRun: python3 scripts/sync-readme-facts.py", file=sys.stderr)
            return 1
        print("OK: README.md matches the committed demo export.")
        return 0

    README.write_text(_replace(current, block))
    print(f"Updated README.md ({len(_rows())} published runs).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
