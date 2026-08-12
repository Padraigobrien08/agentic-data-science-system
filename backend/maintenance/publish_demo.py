"""
Publish or revoke a recorded investigation on the public replay tier.

An operator action, not an API: publishing is the single step that makes something in this
system readable without a token, so it belongs at the console with database access rather than
behind a route someone could reach with a stolen admin token.

    python -m backend.maintenance.publish_demo list
    python -m backend.maintenance.publish_demo publish <investigation-id> --slug edgar-margin-deterioration
    python -m backend.maintenance.publish_demo unpublish edgar-margin-deterioration

Publishing exposes the investigation *and every artifact on its analysis run*. Read what you
are publishing first — ``list`` shows what is currently public. See
``docs/decisions/2026-08-11-showcase-direction.md`` (D3, S1).
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from uuid import UUID

from backend.db.session import SessionLocal
from backend.services.demo_publication_service import (
    DemoNotFound,
    InvalidDemoSlug,
    list_published,
    publish,
    unpublish,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m backend.maintenance.publish_demo",
        description="Manage the public replay tier (recorded investigations).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("list", help="Show currently published demos.")

    pub = sub.add_parser("publish", help="Publish an investigation under a public slug.")
    pub.add_argument("investigation_id", help="Investigation UUID (see /v1/investigations).")
    pub.add_argument(
        "--slug",
        required=True,
        help="Public URL segment: lowercase words separated by single hyphens.",
    )

    unpub = sub.add_parser("unpublish", help="Revoke public access for a slug.")
    unpub.add_argument("slug", help="The published slug to revoke.")

    return parser


def _describe(row) -> str:
    return (
        f"{row.demo_slug}\t{row.id}\tstatus={row.status}\t"
        f"run={row.analysis_run_id}\tcreated={row.created_at:%Y-%m-%d}"
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    with SessionLocal() as session:
        if args.command == "list":
            rows = list_published(session)
            if not rows:
                print("No demos published.")
                return 0
            print(f"{len(rows)} published:")
            for row in rows:
                print("  " + _describe(row))
            return 0

        if args.command == "publish":
            try:
                investigation_id = UUID(args.investigation_id)
            except ValueError:
                print(f"error: {args.investigation_id!r} is not a valid UUID")
                return 2
            try:
                row = publish(session, investigation_id, args.slug)
            except InvalidDemoSlug as exc:
                print(f"error: {exc}")
                return 2
            except DemoNotFound:
                print(f"error: no investigation {investigation_id}")
                return 2
            session.commit()
            print(f"published: {_describe(row)}")
            print(
                "  This is now readable at GET /v1/demos/"
                f"{row.demo_slug} with no authentication, including its artifacts."
            )
            return 0

        try:
            row = unpublish(session, args.slug)
        except DemoNotFound:
            print(f"error: no published demo for {args.slug!r}")
            return 2
        session.commit()
        print(f"unpublished: {args.slug} (investigation {row.id} is private again)")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
