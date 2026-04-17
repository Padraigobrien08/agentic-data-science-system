"""Explicit retention maintenance workflow for run and model payload history."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from backend.config.settings import Settings, get_settings
from backend.db.session import SessionLocal
from backend.repositories.analysis_run_repository import AnalysisRunRepository
from backend.repositories.model_call_repository import ModelCallRepository


def _positive_int(raw: str) -> int:
    value = int(raw)
    if value <= 0:
        raise argparse.ArgumentTypeError("value must be greater than zero")
    return value


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _empty_report(*, dry_run: bool) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "run_candidates": 0,
        "model_call_candidates": 0,
        "runs_compacted": 0,
        "model_calls_redacted": 0,
        "errors": [],
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.maintenance.retention",
        description="Dry-run or apply retention for stored run and model payload history.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        dest="dry_run",
        action="store_true",
        help="Report eligible run and model payload candidates without mutating them.",
    )
    mode.add_argument(
        "--apply",
        dest="dry_run",
        action="store_false",
        help="Apply retention by compacting run payloads and redacting model payloads.",
    )
    parser.set_defaults(dry_run=True)
    parser.add_argument(
        "--limit",
        type=_positive_int,
        default=None,
        help="Override the per-tier batch size for this invocation.",
    )
    parser.add_argument(
        "--json",
        dest="json_output",
        action="store_true",
        help="Print the retention report as JSON.",
    )
    return parser


def run_retention_maintenance(
    session: Session,
    *,
    settings: Settings | None = None,
    dry_run: bool = True,
    limit: int | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    cfg = settings if settings is not None else get_settings()
    current_time = now if now is not None else _utc_now()
    batch_limit = limit if limit is not None else cfg.retention_batch_size
    report = _empty_report(dry_run=dry_run)
    runs = AnalysisRunRepository(session)
    model_calls = ModelCallRepository(session)

    try:
        run_candidates = []
        if cfg.retention_run_payload_days > 0:
            run_candidates = runs.list_compaction_candidates(
                finished_before=current_time - timedelta(days=cfg.retention_run_payload_days),
                limit=batch_limit,
            )
        report["run_candidates"] = len(run_candidates)

        model_call_candidates = []
        if cfg.retention_model_payload_days > 0:
            model_call_candidates = model_calls.list_payload_redaction_candidates(
                created_before=current_time - timedelta(days=cfg.retention_model_payload_days),
                limit=batch_limit,
            )
        report["model_call_candidates"] = len(model_call_candidates)

        if dry_run:
            return report

        for row in run_candidates:
            row.input_payload_json = None
            row.output_payload_json = None
            row.compacted_at = current_time

        for row in model_call_candidates:
            row.request_payload_json = None
            row.response_payload_json = None
            row.payloads_redacted_at = current_time

        session.commit()
        report["runs_compacted"] = len(run_candidates)
        report["model_calls_redacted"] = len(model_call_candidates)
        return report
    except Exception as exc:  # noqa: BLE001
        session.rollback()
        report["errors"].append(f"{type(exc).__name__}: {exc}")
        return report


def format_retention_report(report: dict[str, Any], *, json_output: bool) -> str:
    if json_output:
        return json.dumps(report, indent=2, default=str)

    lines = [
        f"dry_run={report['dry_run']}",
        f"run_candidates={report['run_candidates']}",
        f"model_call_candidates={report['model_call_candidates']}",
        f"runs_compacted={report['runs_compacted']}",
        f"model_calls_redacted={report['model_calls_redacted']}",
    ]
    errors = report.get("errors") or []
    if errors:
        lines.append("errors=" + "; ".join(str(item) for item in errors))
    else:
        lines.append("errors=[]")
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    settings = get_settings()
    with SessionLocal() as session:
        report = run_retention_maintenance(
            session,
            settings=settings,
            dry_run=args.dry_run,
            limit=args.limit,
        )
    print(format_retention_report(report, json_output=args.json_output))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
