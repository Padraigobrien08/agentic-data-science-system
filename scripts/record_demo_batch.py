"""
Record the whole demo stack unattended.

Drives ``scripts/record_demo.py`` once per entry in ``demo/recording-stack.toml``, so a set
of recordings is one command instead of eight, and the goals themselves live in a reviewable
file rather than in shell history.

    python3 scripts/record_demo_batch.py --list          # what would run, and why
    python3 scripts/record_demo_batch.py --dry-run       # resolve everything, spend nothing
    python3 scripts/record_demo_batch.py                 # record all, dump after each
    python3 scripts/record_demo_batch.py --only edgar-peer-separation

This spends real money and, for EDGAR entries, reaches the SEC.

Three deliberate refusals:

*Nothing is published.* A published demo is a claim about the system, and the outcome of a
real run is not known until it finishes. Record, read the summary, then publish the subset
that covers the outcome space with ``backend.maintenance.publish_demo``.

*Nothing is retried.* A failed run still made model calls that were charged. Retrying on
your behalf would double a bill you did not agree to, so failures are reported and the batch
moves on.

*Nothing runs past the ceiling.* ``--max-spend-usd`` is checked between runs against actual
recorded spend, so a pathological run cannot drain an account while unattended.
"""

from __future__ import annotations

import argparse
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import scripts.record_demo as record_demo  # noqa: E402
from backend.db.session import SessionLocal  # noqa: E402
from backend.models.analysis_run import AnalysisRun  # noqa: E402
from backend.models.investigation import Investigation  # noqa: E402

STACK_FILE = REPO_ROOT / "demo" / "recording-stack.toml"


@dataclass(frozen=True)
class Recording:
    id: str
    command: str
    goal: str
    intent: str = ""
    expect: str = ""
    why: str = ""
    slug: str | None = None
    tickers: str | None = None
    optional: bool = False


def load_stack(path: Path = STACK_FILE) -> list[Recording]:
    if not path.is_file():
        raise SystemExit(f"No recording stack at {path}")
    raw = tomllib.loads(path.read_text(encoding="utf-8"))
    entries = raw.get("recording") or []
    if not entries:
        raise SystemExit(f"{path} defines no [[recording]] entries.")

    out: list[Recording] = []
    seen: set[str] = set()
    for entry in entries:
        missing = [k for k in ("id", "command", "goal") if not entry.get(k)]
        if missing:
            raise SystemExit(f"{path}: an entry is missing {', '.join(missing)}")
        if entry["command"] not in {"csv", "edgar"}:
            raise SystemExit(f"{path}: {entry['id']} has unknown command {entry['command']!r}")
        if entry["id"] in seen:
            raise SystemExit(f"{path}: duplicate id {entry['id']!r}")
        seen.add(entry["id"])
        out.append(Recording(**{k: v for k, v in entry.items() if k in Recording.__annotations__}))
    return out


def _argv_for(rec: Recording, *, dump: bool) -> list[str]:
    """The exact `record_demo.py` invocation for this entry."""
    argv = [rec.command, "--goal", rec.goal, "--chat"]
    if rec.command == "edgar" and rec.tickers:
        argv += ["--tickers", rec.tickers]
    if dump:
        argv.append("--dump")
    # --publish is intentionally never passed; see the module docstring.
    return argv


def _latest_run_id(after: Any) -> UUID | None:
    """The newest analysis run, used to attribute spend to the entry that just ran."""
    from sqlalchemy import select

    with SessionLocal() as db:
        stmt = select(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(1)
        if after is not None:
            stmt = (
                select(AnalysisRun)
                .where(AnalysisRun.created_at > after)
                .order_by(AnalysisRun.created_at.desc())
                .limit(1)
            )
        row = db.scalar(stmt)
        return row.id if row else None


def _outcome(run_id: UUID | None) -> tuple[str, str, float, int]:
    """(status, termination reason, spend, model calls) for a finished run."""
    if run_id is None:
        return ("?", "?", 0.0, 0)
    from sqlalchemy import select

    with SessionLocal() as db:
        inv = db.scalar(select(Investigation).where(Investigation.analysis_run_id == run_id))
        cost, priced, calls = record_demo._spend_for_run(db, run_id)
        if inv is None:
            return ("no investigation", "-", cost if priced else 0.0, calls)
        reason = (inv.termination_json or {}).get("reason", "-")
        return (str(inv.status), str(reason), cost if priced else 0.0, calls)


def _now() -> Any:
    from sqlalchemy import func, select

    with SessionLocal() as db:
        return db.scalar(select(func.max(AnalysisRun.created_at)))


def _print_stack(stack: list[Recording]) -> None:
    for rec in stack:
        flag = "  (optional)" if rec.optional else ""
        print(f"\n{rec.id}{flag}")
        print(f"  command  {rec.command}" + (f" --tickers {rec.tickers}" if rec.tickers else ""))
        print(f"  intent   {rec.intent or '-'}")
        print(f"  aiming for  {rec.expect or '-'}")
        print(f"  goal     {rec.goal}")
        if rec.why:
            print("  why      " + rec.why.strip().replace("\n", "\n           "))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 scripts/record_demo_batch.py",
        description="Record every goal in demo/recording-stack.toml.",
    )
    parser.add_argument("--list", action="store_true", help="Print the stack and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Show the invocations, spend nothing.")
    parser.add_argument("--only", action="append", metavar="ID", help="Record just this id (repeatable).")
    parser.add_argument(
        "--include-known-limit",
        action="store_true",
        help="Also record entries marked optional (the documented model-failure case).",
    )
    parser.add_argument("--no-dump", action="store_true", help="Skip the per-run database snapshot.")
    parser.add_argument(
        "--max-spend-usd",
        type=float,
        default=5.0,
        help="Stop before the next run once recorded spend exceeds this (default: 5.0).",
    )
    args = parser.parse_args(argv)

    stack = load_stack()
    if args.only:
        wanted = set(args.only)
        unknown = wanted - {r.id for r in stack}
        if unknown:
            raise SystemExit(f"Unknown id(s): {', '.join(sorted(unknown))}")
        stack = [r for r in stack if r.id in wanted]
    elif not args.include_known_limit:
        stack = [r for r in stack if not r.optional]

    if args.list:
        _print_stack(stack)
        return 0

    if args.dry_run:
        print(f"{len(stack)} recording(s) would run:\n")
        for rec in stack:
            print(f"  record_demo.py {' '.join(_argv_for(rec, dump=not args.no_dump))}")
        print("\nNothing was recorded and nothing was charged.")
        return 0

    print(f"Recording {len(stack)} goal(s). This makes real model calls.")
    print(f"Spend ceiling: ${args.max_spend_usd:.2f} (checked between runs).\n")

    results: list[tuple[Recording, str, str, float, int]] = []
    spent = 0.0

    for i, rec in enumerate(stack, start=1):
        if spent > args.max_spend_usd:
            print(f"\nstopping: ${spent:.4f} recorded exceeds the ${args.max_spend_usd:.2f} ceiling.")
            print(f"{len(stack) - i + 1} recording(s) not run. Raise --max-spend-usd to continue.")
            break

        print("=" * 72)
        print(f"[{i}/{len(stack)}] {rec.id} — aiming for: {rec.expect or 'any outcome'}")
        print("=" * 72)

        before = _now()
        try:
            code = record_demo.main(_argv_for(rec, dump=not args.no_dump))
        except SystemExit as exc:  # record_demo raises this for operator errors
            code = int(exc.code or 1)
        except Exception as exc:  # noqa: BLE001 — one bad goal must not abandon the rest
            print(f"  {rec.id} raised {type(exc).__name__}: {exc}")
            code = 1

        run_id = _latest_run_id(before)
        status, reason, cost, calls = _outcome(run_id)
        spent += cost
        if code != 0:
            status = f"FAILED({code}) {status}"
        results.append((rec, status, reason, cost, calls))

    print("\n" + "=" * 72)
    print("SUMMARY")
    print("=" * 72)
    print(f"{'id':<28} {'status':<22} {'termination':<22} {'calls':>5} {'usd':>8}")
    for rec, status, reason, cost, calls in results:
        print(f"{rec.id:<28} {status:<22} {reason:<22} {calls:>5} {cost:>8.4f}")
    print(f"\ntotal recorded spend: ${spent:.4f}")

    reasons = {r for _, _, r, _, _ in results}
    print(f"outcomes covered: {', '.join(sorted(x for x in reasons if x not in {'-', '?'})) or 'none'}")
    if "insufficient_evidence" not in reasons:
        print("note: nothing declined this time. A set where everything concludes is the weaker set.")

    print(
        "\nNothing was published. Review the runs, then publish the subset you want:\n"
        "  python -m backend.maintenance.publish_demo publish <investigation_id> --slug <slug>\n"
        "  python3 scripts/export_demo_static.py"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
