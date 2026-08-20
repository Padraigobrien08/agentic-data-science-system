"""
Export the published replay-tier demos as static files for the frontend.

The static replay showcase (docs/decisions/2026-08-14-static-replay-showcase.md, D9) serves
the recorded investigations from committed files instead of a live backend. The rule that
makes that safe: **the static path serves the same bytes the API would.** So this script goes
through exactly the service and schema builders the public routes use — ``list_published`` +
``build_summary`` for the index, ``get_published`` + ``build_detail`` per slug — and copies
artifact blobs out of artifact storage. There is no parallel serialization to drift.

    python3 scripts/export_demo_static.py            # writes into frontend/
    python3 scripts/export_demo_static.py --check    # verify the committed export is current

Outputs (committed to the repo):

    frontend/src/lib/demo-static/index.json         GET /v1/demos
    frontend/src/lib/demo-static/{slug}.json        GET /v1/demos/{slug}
    frontend/src/lib/demo-static/{slug}.capture.json  model calls + chat turns (see below)
    frontend/src/lib/demo-static/artifacts.json     slug -> artifact id -> public href
    frontend/public/demo-data/{slug}/artifacts/{id}/{filename}   blob bytes

The capture bundle is the one thing here that is *not* a public API response: model payloads
are admin-gated on the live API, and publishing a demo is a separate deliberate act. See
``backend.schemas.demo_capture``.

Recorded runs cost real money, so the export refuses to write a demo whose expensive parts
have already been destroyed — a model payload redacted by retention, or an artifact blob
pruned — rather than silently emitting a hollow replay. ``--allow-degraded`` downgrades those
to warnings when that is genuinely intended.

Run against the database holding the published demos (local ``.env`` by default). Operator
script: reads the DB and writes into the working tree, never the reverse.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from sqlalchemy import select  # noqa: E402

from backend.config.settings import get_settings  # noqa: E402
from backend.db.session import SessionLocal  # noqa: E402
from backend.llm.pricing import parse_model_prices  # noqa: E402
from backend.models.artifact import Artifact  # noqa: E402
from backend.models.chat_message import ChatMessage  # noqa: E402
from backend.models.conversation import Conversation  # noqa: E402
from backend.models.model_call import ModelCall  # noqa: E402
from backend.schemas.demo_capture import build_demo_capture  # noqa: E402
from backend.schemas.investigation import build_detail, build_summary  # noqa: E402
from backend.services.demo_publication_service import list_published  # noqa: E402
from backend.storage.resolver import open_reader  # noqa: E402

STATIC_DIR = REPO_ROOT / "frontend" / "src" / "lib" / "demo-static"
BLOB_DIR = REPO_ROOT / "frontend" / "public" / "demo-data"

#: Blob directories the exporter writes are named by artifact id; pruning matches only these
#: so it can never remove something a human put under public/demo-data by hand.
UUID_DIR = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")

#: Names come from experiment metadata; keep only characters safe in a URL path segment.
_FILENAME_SAFE = re.compile(r"[^A-Za-z0-9._-]+")

#: Artifact names are recorded without extensions. Vercel types a static file by its
#: extension alone, so without this every artifact downloads as application/octet-stream —
#: evidence a reviewer cannot open is not evidence.
_MIME_SUFFIX = {
    "text/csv": ".csv",
    "application/json": ".json",
    "application/vnd.chart+json": ".json",
    "text/markdown": ".md",
    "text/plain": ".txt",
}


def _safe_filename(name: str, mime_type: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    cleaned = _FILENAME_SAFE.sub("-", normalized).strip("-.") or "artifact"
    suffix = _MIME_SUFFIX.get((mime_type or "").split(";", 1)[0].strip().lower(), "")
    if suffix and not cleaned.lower().endswith(suffix):
        cleaned += suffix
    return cleaned


def _dump(payload: object) -> str:
    # Stable formatting so re-running the export produces reviewable diffs.
    return json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _capture_for(db, row, *, prices) -> tuple[object, list[str]]:
    """The capture bundle for one published demo, plus anything retention already destroyed."""
    run_id = row.analysis_run_id
    losses: list[str] = []
    if run_id is None:
        return (
            build_demo_capture(
                demo_slug=row.demo_slug,
                investigation_id=row.id,
                analysis_run_id=None,
                model_call_rows=[],
                conversation_rows=[],
                prices=prices,
            ),
            losses,
        )

    calls = list(db.scalars(select(ModelCall).where(ModelCall.analysis_run_id == run_id)).all())
    redacted = [c for c in calls if c.payloads_redacted_at is not None]
    if redacted:
        losses.append(
            f"{row.demo_slug}: {len(redacted)}/{len(calls)} model payloads already redacted by "
            f"retention — the prompts and responses are gone and cannot be re-exported. "
            f"Set EDGAR_BACKEND_RETENTION_MODEL_PAYLOAD_DAYS=0 on the recording box."
        )

    convo_ids = select(ChatMessage.conversation_id).where(ChatMessage.analysis_run_id == run_id)
    conversations = list(db.scalars(select(Conversation).where(Conversation.id.in_(convo_ids))).all())

    return (
        build_demo_capture(
            demo_slug=row.demo_slug,
            investigation_id=row.id,
            analysis_run_id=run_id,
            model_call_rows=calls,
            conversation_rows=conversations,
            prices=prices,
        ),
        losses,
    )


def _prune_orphan_blobs(artifact_hrefs: dict[str, dict[str, str]]) -> None:
    """
    Delete blob directories no published demo references any more.

    Artifact ids are per-run, so re-publishing a slug under a fresh recording writes a new set
    of directories and strands the old one. Nothing removed them, so every re-publish left a
    full set of dead files behind — committed, deployed and served forever. Scoped to slugs in
    this export and to directories named like the artifact ids the exporter itself writes, so
    it can only remove things this script created.
    """
    # Resolved from REPO_ROOT at call time, exactly as the write path does. The module-level
    # BLOB_DIR is fixed at import, so using it here would prune a different tree than the one
    # just written whenever REPO_ROOT is redirected — which is how the tests run.
    blob_root = REPO_ROOT / "frontend" / "public" / "demo-data"
    for slug, hrefs in artifact_hrefs.items():
        root = blob_root / slug / "artifacts"
        if not root.is_dir():
            continue
        keep = {href.rsplit("/", 2)[-2] for href in hrefs.values()}
        for child in root.iterdir():
            if not child.is_dir() or child.name in keep:
                continue
            if not UUID_DIR.fullmatch(child.name):
                continue
            shutil.rmtree(child)
            print(f"pruned orphaned blob {slug}/{child.name}")


def build_export(*, allow_degraded: bool = False, prune: bool = True) -> tuple[dict[str, str], int]:
    """Render every file of the export as {relative path: content}; blobs counted separately."""
    settings = get_settings()
    prices = parse_model_prices(settings.llm_model_prices)
    text_files: dict[str, str] = {}
    blob_bytes = 0
    #: Things already lost in the database. Collected in full rather than raised on the first,
    #: so one run of the export tells the operator everything a re-record would have to cover.
    losses: list[str] = []

    with SessionLocal() as db:
        rows = list_published(db)
        if not rows:
            raise SystemExit("No published demos in this database; nothing to export.")

        index = [build_summary(row).model_dump(mode="json") for row in rows]
        text_files["src/lib/demo-static/index.json"] = _dump(index)

        artifact_hrefs: dict[str, dict[str, str]] = {}
        for row in rows:
            slug = row.demo_slug
            detail = build_detail(row)
            text_files[f"src/lib/demo-static/{slug}.json"] = _dump(detail.model_dump(mode="json"))

            capture, capture_losses = _capture_for(db, row, prices=prices)
            losses.extend(capture_losses)
            text_files[f"src/lib/demo-static/{slug}.capture.json"] = _dump(
                capture.model_dump(mode="json")
            )
            if not capture.model_calls:
                print(f"  note: {slug} has no model calls recorded (fixture policy, or a run "
                      f"predating model-call capture)")

            hrefs: dict[str, str] = {}
            for experiment in detail.experiments:
                for ref in experiment.artifacts:
                    artifact = db.get(Artifact, UUID(str(ref.id)))
                    # Previously skipped in silence, which produces a demo whose evidence links
                    # resolve to nothing — the one failure a replay must never ship with.
                    if artifact is None:
                        losses.append(f"{slug}: artifact {ref.id} ({ref.name}) is missing from the database.")
                        continue
                    if artifact.blob_deleted_at is not None:
                        losses.append(
                            f"{slug}: artifact {ref.id} ({ref.name}) had its blob pruned by retention "
                            f"on {artifact.blob_deleted_at:%Y-%m-%d} — the evidence bytes are gone."
                        )
                        continue
                    filename = _safe_filename(ref.name, ref.mime_type)
                    rel = Path("public") / "demo-data" / slug / "artifacts" / str(ref.id) / filename
                    with open_reader(artifact.storage_uri, settings=settings) as fh:
                        data = fh.read()
                    target = REPO_ROOT / "frontend" / rel
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                    blob_bytes += len(data)
                    hrefs[str(ref.id)] = f"/demo-data/{slug}/artifacts/{ref.id}/{filename}"
            artifact_hrefs[slug] = hrefs

        if prune:
            _prune_orphan_blobs(artifact_hrefs)

        text_files["src/lib/demo-static/artifacts.json"] = _dump(artifact_hrefs)
        text_files["src/lib/demo-static/generated.ts"] = _generated_ts(
            [row.demo_slug for row in rows]
        )

    if losses:
        header = "Recorded content is already gone in this database:"
        body = "\n".join(f"  - {m}" for m in losses)
        if not allow_degraded:
            raise SystemExit(
                f"{header}\n{body}\n\n"
                "Exporting now would publish a degraded replay. Restore from a recording dump\n"
                "(scripts/record_demo.py --dump) or re-record. Pass --allow-degraded to export anyway."
            )
        print(f"WARNING: {header}\n{body}")

    return text_files, blob_bytes


def _generated_ts(slugs: list[str]) -> str:
    """
    Typed entry point over the exported JSON.

    Generated rather than hand-written so adding or renaming a published demo cannot leave a
    dangling import — the slug list and the import list come from the same query.
    """
    imports = "\n".join(
        f'import detail{i} from "./{slug}.json";\nimport capture{i} from "./{slug}.capture.json";'
        for i, slug in enumerate(slugs)
    )
    entries = ",\n".join(
        f'  "{slug}": detail{i} as unknown as InvestigationDetail' for i, slug in enumerate(slugs)
    )
    capture_entries = ",\n".join(
        f'  "{slug}": capture{i} as unknown as DemoCapture' for i, slug in enumerate(slugs)
    )
    return f"""// Generated by scripts/export_demo_static.py — do not edit by hand.
import type {{ InvestigationDetail, InvestigationSummary }} from "@/lib/api/types";

import type {{ DemoCapture }} from "./capture-types";
import artifactHrefs from "./artifacts.json";
import index from "./index.json";
{imports}

export const DEMO_INDEX = index as unknown as InvestigationSummary[];

export const DEMO_DETAILS: Record<string, InvestigationDetail> = {{
{entries},
}};

/** Model calls and chat turns behind each demo — see backend/schemas/demo_capture.py. */
export const DEMO_CAPTURES: Record<string, DemoCapture> = {{
{capture_entries},
}};

export const DEMO_ARTIFACT_HREFS: Record<string, Record<string, string>> =
  artifactHrefs as Record<string, Record<string, string>>;
"""


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python3 scripts/export_demo_static.py", description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if the committed JSON differs from what the database would export.",
    )
    parser.add_argument(
        "--allow-degraded",
        action="store_true",
        help="Export even when model payloads or artifact blobs have already been destroyed.",
    )
    args = parser.parse_args(argv)

    text_files, blob_bytes = build_export(allow_degraded=args.allow_degraded, prune=not args.check)

    if args.check:
        stale = []
        for rel, content in text_files.items():
            path = REPO_ROOT / "frontend" / rel
            if not path.is_file() or path.read_text(encoding="utf-8") != content:
                stale.append(rel)
        if stale:
            print("Static demo export is stale; re-run scripts/export_demo_static.py:")
            for rel in stale:
                print(f"  {rel}")
            raise SystemExit(1)
        print(f"Static demo export is current ({len(text_files)} files).")
        return

    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    for rel, content in text_files.items():
        path = REPO_ROOT / "frontend" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(f"wrote {rel}")
    print(f"artifact blobs: {blob_bytes / 1024:.1f} KB under {BLOB_DIR.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
