"""
CLI entry: ``python -m orchestration.agent --tickers AAPL MSFT --goal "..."``.

Ensures the repo root is on ``sys.path`` so ``edgar_project`` imports work without install.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from edgar_project.orchestration import OrchestrationInput, run_analysis_agent


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Phase 3 orchestration: plan + MCP execution.")
    parser.add_argument("--tickers", nargs="+", required=True, metavar="SYM", help="US equity symbols")
    parser.add_argument("--goal", required=True, help='Analysis goal, e.g. "find unusual financial changes"')
    parser.add_argument("--refresh", action="store_true", help="Bypass cache on fetch steps (MCP)")
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print full OrchestrationOutput as JSON",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Log orchestration run state (run_id, plan, steps, outcomes) to stderr",
    )
    args = parser.parse_args(argv)

    if args.verbose:
        orch = logging.getLogger("edgar_project.orchestration")
        orch.setLevel(logging.INFO)
        if not orch.handlers:
            _h = logging.StreamHandler(sys.stderr)
            _h.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
            orch.addHandler(_h)

    req = OrchestrationInput(tickers=args.tickers, analysis_goal=args.goal, refresh=args.refresh)
    out = run_analysis_agent(req)

    if args.as_json:
        print(json.dumps(out.model_dump(mode="json"), indent=2))
    else:
        print(out.final_summary or out.message)
        if out.final_report_path:
            print(f"report: {out.final_report_path}")
        for e in out.errors:
            print(f"error [{e.code}]: {e.message}", file=sys.stderr)
        for w in out.warnings:
            print(f"warning [{w.code}]: {w.message}", file=sys.stderr)

    ok = out.status.value in ("success", "partial_success")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
