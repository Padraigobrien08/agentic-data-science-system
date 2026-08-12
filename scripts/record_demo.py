"""
Record a real investigation for the public replay tier.

This spends money and, for the EDGAR case, reaches the SEC. It is an operator script run
deliberately, not part of any request path.

    python3 scripts/record_demo.py csv   --goal "..." [--publish csv-delivery-delays]
    python3 scripts/record_demo.py edgar --goal "..." --tickers AAPL,MSFT,NVDA

Prints the outcome and the estimated spend, then the investigation id to hand to
``python -m backend.maintenance.publish_demo``. Nothing is published unless ``--publish`` is
given, so a recording can be inspected before it is exposed.

See ``docs/decisions/2026-08-11-showcase-direction.md`` (S1) and ``docs/demo-script.md``.
"""

from __future__ import annotations

import argparse
import csv
import sys
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from backend.config.settings import get_settings
from backend.db.session import SessionLocal
from backend.llm.pricing import estimate_cost_usd, parse_model_prices
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import UserAccessTier
from backend.models.investigation import Investigation
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.user import User
from backend.security.passwords import hash_password
from backend.services.agentic_investigation_execution_service import (
    AgenticInvestigationExecutionService,
)
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.demo_publication_service import publish

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CSV = REPO_ROOT / "demo" / "datasets" / "operational_delivery.csv"
RECORDER_EMAIL = "demo-recorder@guest.example.com"


def _recorder(session) -> User:
    """A dedicated adaptive-tier account, so recordings are attributable and entitled."""
    user = session.scalar(select(User).where(User.email == RECORDER_EMAIL))
    if user is None:
        user = User(
            email=RECORDER_EMAIL,
            display_name="Demo recorder",
            hashed_password=hash_password("unused-recordings-are-made-by-cli"),
            access_tier=UserAccessTier.adaptive,
            is_admin=True,  # exempt from the spend ceilings; recording is the operator's call
        )
        session.add(user)
        session.flush()
    elif user.access_tier is not UserAccessTier.adaptive:
        user.access_tier = UserAccessTier.adaptive
        session.flush()
    return user


def _project(session, user: User, name: str) -> Project:
    project = session.scalar(
        select(Project).where(Project.owner_user_id == user.id, Project.name == name)
    )
    if project is None:
        project = Project(owner_user_id=user.id, name=name, description="Recorded demo runs.")
        session.add(project)
        session.flush()
    return project


def _read_records(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise SystemExit(f"error: {path} has no rows")
    numeric = ("avg_delivery_days", "order_volume", "on_time_rate", "staff_count")
    for row in rows:
        for key in numeric:
            if key in row and row[key] != "":
                row[key] = float(row[key]) if "." in row[key] else int(row[key])
    return rows


def _spend_for_run(session, run_id: UUID) -> tuple[float, bool, int]:
    settings = get_settings()
    prices = parse_model_prices(settings.llm_model_prices)
    calls = list(session.scalars(select(ModelCall).where(ModelCall.analysis_run_id == run_id)).all())
    if not prices:
        return 0.0, False, len(calls)
    total = sum(
        estimate_cost_usd(
            prices,
            model=call.model_name or "",
            prompt_tokens=call.prompt_tokens,
            completion_tokens=call.completion_tokens,
        )
        for call in calls
    )
    return total, True, len(calls)


def _report(session, run_id: UUID) -> UUID | None:
    investigation = session.scalar(
        select(Investigation).where(Investigation.analysis_run_id == run_id)
    )
    run = session.get(AnalysisRun, run_id)
    cost, priced, call_count = _spend_for_run(session, run_id)

    print("\n" + "=" * 68)
    print(f"analysis_run   {run_id}")
    print(f"run status     {run.status.value if run else '?'}")
    if investigation is None:
        print("investigation  (none persisted)")
        print("=" * 68)
        return None

    termination = investigation.termination_json or {}
    print(f"investigation  {investigation.id}")
    print(f"status         {investigation.status}")
    print(f"termination    {termination.get('reason', '?')}")
    print(f"confidence     {investigation.confidence}")
    print(f"hypotheses     {len(investigation.hypotheses)}")
    print(f"evidence       {len(investigation.evidence)}")
    print(f"experiments    {len(investigation.experiment_results)}")
    print(f"critiques      {len(investigation.critiques)}")
    print(f"model calls    {call_count}")
    print(f"est. spend     ${cost:.4f}" if priced else "est. spend     (unpriced)")

    if investigation.hypotheses:
        print("\nhypotheses:")
        for h in investigation.hypotheses:
            print(f"  [{h.status}] {(h.statement or '')[:88]}")
    print("=" * 68)
    return investigation.id


def _execute(payload: dict, *, goal: str, project_name: str, publish_slug: str | None) -> int:
    settings = get_settings()
    if not settings.agentic_engine_enabled:
        print(
            "error: the agentic engine is disabled.\n"
            "       Set EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true for this recording."
        )
        return 2
    if settings.llm_provider.strip().lower() == "off":
        print("error: EDGAR_BACKEND_LLM_PROVIDER is 'off'; a recording needs a real model.")
        return 2

    with SessionLocal() as session:
        user = _recorder(session)
        project = _project(session, user, project_name)
        run = AnalysisRunService(session).create(
            project.id,
            initiated_by_user_id=user.id,
            orchestration_goal_text=goal,
            input_payload_json=payload,
        )
        session.commit()
        run_id = run.id
        print(f"created analysis_run {run_id} — executing (this makes real model calls)…")

        try:
            AgenticInvestigationExecutionService(session).execute_analysis_run(run_id)
        except Exception as exc:  # noqa: BLE001 — operator script: report and keep the trace
            session.rollback()
            print(f"\nexecution failed: {type(exc).__name__}: {exc}")
            _report(session, run_id)
            return 1

        session.commit()
        investigation_id = _report(session, run_id)

        if publish_slug and investigation_id is not None:
            publish(session, investigation_id, publish_slug)
            session.commit()
            print(f"\npublished at GET /v1/demos/{publish_slug} (no authentication)")
        elif investigation_id is not None:
            print(
                "\nnot published. To publish:\n"
                f"  python -m backend.maintenance.publish_demo publish {investigation_id} --slug <slug>"
            )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 scripts/record_demo.py",
        description="Record a real investigation for the public replay tier.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--goal", required=True, help="The investigation goal, in plain language.")
    common.add_argument("--publish", default=None, metavar="SLUG", help="Publish on success.")

    c = sub.add_parser("csv", parents=[common], help="Record over a local tabular dataset.")
    c.add_argument("--path", type=Path, default=DEFAULT_CSV)
    c.add_argument("--time-field", default="month")
    c.add_argument("--entity-fields", default="region")

    e = sub.add_parser("edgar", parents=[common], help="Record over live SEC data.")
    e.add_argument("--tickers", default="AAPL,MSFT,NVDA")
    e.add_argument("--refresh", action="store_true", help="Force a fresh SEC fetch.")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    if args.command == "csv":
        if not args.path.exists():
            print(f"error: {args.path} not found — run scripts/build_demo_dataset.py first")
            return 2
        records = _read_records(args.path)
        payload = {
            "engine": "agentic",
            "analysis_goal": args.goal,
            "dataset": {
                "adapter": "in_memory",
                "name": args.path.stem,
                "records": records,
                "time_field": args.time_field,
                "entity_id_fields": [f.strip() for f in args.entity_fields.split(",") if f.strip()],
            },
        }
        print(f"dataset: {args.path.name} ({len(records)} rows)")
        return _execute(
            payload,
            goal=args.goal,
            project_name="Recorded demos (tabular)",
            publish_slug=args.publish,
        )

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    payload = {
        "engine": "agentic",
        "analysis_goal": args.goal,
        "tickers": tickers,
        "refresh": bool(args.refresh),
        "dataset": {"adapter": "edgar", "entities": tickers},
    }
    print(f"tickers: {', '.join(tickers)} (this fetches from the SEC)")
    return _execute(
        payload,
        goal=args.goal,
        project_name="Recorded demos (EDGAR)",
        publish_slug=args.publish,
    )


if __name__ == "__main__":
    sys.exit(main())
