"""
Record a real investigation for the public replay tier.

This spends money and, for the EDGAR case, reaches the SEC. It is an operator script run
deliberately, not part of any request path.

    python3 scripts/record_demo.py csv   --goal "..." [--publish csv-delivery-delays]
    python3 scripts/record_demo.py edgar --goal "..." --tickers AAPL,MSFT,NVDA

Prints the outcome and the estimated spend, then the investigation id to hand to
``python -m backend.maintenance.publish_demo``. Nothing is published unless ``--publish`` is
given, so a recording can be inspected before it is exposed.

``--chat`` additionally records the turn the way the product actually produces one: a
conversation, a user message carrying the goal, the run, then an assistant message linked to
that run. Pass ``--conversation`` with a printed id to append a follow-up turn to the same
thread. This exists because the replay tier renders the *chat* surface — and a thread
assembled by hand afterwards would be a reconstruction, not a recording.

``--dump`` snapshots the database afterwards, into ``var/demo-dumps/``. Use it for anything
you would not want to pay for twice: retention redacts model payloads 30 days after the call
and prunes artifact blobs at 180, and the export format will keep changing, so the durable
asset is the run itself rather than any one export of it. With a dump on disk, re-exporting
is free forever; without one, it is another API bill.

See ``docs/decisions/2026-08-11-showcase-direction.md`` (S1),
``docs/decisions/2026-08-14-static-replay-showcase.md`` (D9) and ``docs/demo-script.md``.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.engine import make_url

from backend.config.settings import get_settings
from backend.db.session import SessionLocal
from backend.llm.pricing import estimate_cost_usd, parse_model_prices
from backend.models.analysis_run import AnalysisRun
from backend.models.conversation import Conversation
from backend.models.enums import ChatMessageRole, ChatMessageStatus, UserAccessTier
from backend.models.investigation import Investigation
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.user import User
from backend.security.passwords import hash_password
from backend.services.agentic_investigation_execution_service import (
    AgenticInvestigationExecutionService,
)
from backend.services.analysis_run_service import AnalysisRunService
from backend.services.chat_conversation_service import ChatConversationService
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


#: Where recording dumps land. Gitignored: a dump carries every row, including user
#: password hashes, and must never be committed.
DUMP_DIR = REPO_ROOT / "var" / "demo-dumps"

#: The compose service holding the database, used when the host has no `pg_dump`.
DUMP_CONTAINER = os.environ.get("EDGAR_DEMO_DUMP_CONTAINER", "edgar-db-1")


def _dump_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _dump_database(dest: Path) -> bool:
    """
    Snapshot the whole database to ``dest`` (pg_custom format).

    This is the insurance that makes a recording re-exportable forever. Model payloads are
    redacted by retention 30 days after the call, artifact blobs are pruned at 180, and the
    export schema will keep changing — so the run itself, not any one export of it, is the
    thing worth keeping. Re-recording costs real money; a dump costs a few megabytes.

    Restore with::

        pg_restore --clean --if-exists -d "$EDGAR_BACKEND_DATABASE_URL" <dump>
    """
    url = make_url(get_settings().database_url)
    if not url.drivername.startswith("postgresql"):
        print(f"skip dump: {url.drivername} is not PostgreSQL")
        return False

    dest = dest.resolve()
    dest.parent.mkdir(parents=True, exist_ok=True)
    libpq = url.set(drivername="postgresql").render_as_string(hide_password=False)

    if shutil.which("pg_dump"):
        cmd = ["pg_dump", "--no-owner", "--no-privileges", "-Fc", "-f", str(dest), libpq]
        stdout = None
    else:
        # No client on the host — borrow the server container's, which is version-matched
        # to the data by construction.
        cmd = [
            "docker", "exec", DUMP_CONTAINER, "pg_dump",
            "--no-owner", "--no-privileges", "-Fc",
            "-U", url.username or "edgar", "-d", (url.database or "edgar"),
        ]
        stdout = dest.open("wb")

    try:
        result = subprocess.run(cmd, stdout=stdout, stderr=subprocess.PIPE, check=False)
    except FileNotFoundError as exc:
        print(f"dump failed: {exc}. Install postgresql-client, or start the {DUMP_CONTAINER} container.")
        return False
    finally:
        if stdout is not None:
            stdout.close()

    if result.returncode != 0:
        detail = (result.stderr or b"").decode(errors="replace").strip()
        print(f"dump failed (exit {result.returncode}): {detail}")
        dest.unlink(missing_ok=True)
        return False

    # A dump written outside the repo is legitimate (an external archive dir), so fall back
    # to the absolute path rather than failing after the snapshot already succeeded.
    shown = dest.relative_to(REPO_ROOT) if dest.is_relative_to(REPO_ROOT) else dest
    print(f"\ndump           {shown} ({dest.stat().st_size / 1024:.0f} KB)")
    print("               restore: pg_restore --clean --if-exists -d \"$EDGAR_BACKEND_DATABASE_URL\" \\")
    print(f"                          {shown}")
    return True


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


#: The frontend treats this summary as content-free and falls through past it
#: (``isGenericSuccessSummary`` in ``frontend/src/lib/run-primary-view.ts``).
_GENERIC_SUMMARY = re.compile(r"orchestration completed successfully", re.IGNORECASE)


def _assistant_content(run: AnalysisRun | None) -> str:
    """
    The assistant turn's text, derived the way the product derives it.

    ``frontend/src/actions/runs.ts`` persists ``answerCard.narrativeAnswer.thesis``, which for
    these runs resolves to ``rawSummaryLine`` — ``final_summary`` falling back to ``message``
    (``run-primary-view.ts``). Mirrored here rather than invented, so a recorded turn carries
    the same string a live one would. The rendered answer card is rebuilt from the run at
    display time regardless; this text is what the sidebar preview and any non-rendering
    client see.
    """
    payload = (run.output_payload_json if run is not None else None) or {}
    if not isinstance(payload, dict):
        return "Analysis completed, but the narrative preview is not available for this run."
    for key in ("final_summary", "message"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip() and not _GENERIC_SUMMARY.search(value):
            return value.strip()
    return "Analysis completed, but the narrative preview is not available for this run."


def _record_chat_turn(
    session,
    *,
    project: Project,
    user: User,
    goal: str,
    run_id: UUID,
    conversation_id: UUID | None,
) -> Conversation:
    """
    Persist the turn as the chat surface would: user message, run, assistant message.

    The API has no chat→run orchestration — the Next.js server action posts the user message,
    starts the run, then posts the assistant message linked to it
    (``frontend/src/actions/runs.ts``). This reproduces that sequence through the same
    service the route uses, so the thread is a recording rather than a reconstruction.
    """
    chat = ChatConversationService(session)
    if conversation_id is not None:
        conversation = chat.get_conversation(conversation_id)
        if conversation is None:
            raise SystemExit(f"No conversation {conversation_id}; omit --conversation to start one.")
    else:
        # Titled from the first user message by the service, exactly as in the product.
        conversation = chat.create_conversation(project.id, owner_user_id=user.id)

    chat.add_message(conversation, role=ChatMessageRole.user, content=goal)
    run = session.get(AnalysisRun, run_id)
    chat.add_message(
        conversation,
        role=ChatMessageRole.assistant,
        content=_assistant_content(run),
        status=(
            ChatMessageStatus.error
            if run is not None and run.status.value == "error"
            else ChatMessageStatus.complete
        ),
        analysis_run_id=run_id,
        error_summary=(run.error_summary if run is not None else None),
        meta_json={"delivery_mode": "sync_only"},
    )
    return conversation


def _execute(
    payload: dict,
    *,
    goal: str,
    project_name: str,
    publish_slug: str | None,
    chat: bool = False,
    conversation_id: UUID | None = None,
    dump: bool = False,
) -> int:
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
            # Dump even on failure: the calls made before the error were still paid for.
            if dump:
                _dump_database(DUMP_DIR / f"{_dump_stamp()}-{run_id}-failed.dump")
            return 1

        session.commit()
        investigation_id = _report(session, run_id)

        if chat or conversation_id is not None:
            conversation = _record_chat_turn(
                session,
                project=project,
                user=user,
                goal=goal,
                run_id=run_id,
                conversation_id=conversation_id,
            )
            session.commit()
            print(f"\nchat thread    {conversation.id}")
            print(f"               {conversation.title}")
            print(f"  append a follow-up turn:  --conversation {conversation.id}")

        if publish_slug and investigation_id is not None:
            publish(session, investigation_id, publish_slug)
            session.commit()
            print(f"\npublished at GET /v1/demos/{publish_slug} (no authentication)")
        elif investigation_id is not None:
            print(
                "\nnot published. To publish:\n"
                f"  python -m backend.maintenance.publish_demo publish {investigation_id} --slug <slug>"
            )

    # After the session closes, so every commit above is in the snapshot.
    if dump:
        _dump_database(DUMP_DIR / f"{_dump_stamp()}-{publish_slug or run_id}.dump")
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
    common.add_argument(
        "--chat",
        action="store_true",
        help="Also record the turn as a chat thread (user message, run, assistant message).",
    )
    common.add_argument(
        "--conversation",
        default=None,
        metavar="ID",
        type=UUID,
        help="Append this turn to an existing thread instead of starting one (implies --chat).",
    )
    common.add_argument(
        "--dump",
        action="store_true",
        help="Snapshot the database to var/demo-dumps/ afterwards, so this recording can be "
             "re-exported later without paying for the model calls again.",
    )

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
            chat=args.chat,
            conversation_id=args.conversation,
            dump=args.dump,
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
        chat=args.chat,
        conversation_id=args.conversation,
        dump=args.dump,
    )


if __name__ == "__main__":
    sys.exit(main())
