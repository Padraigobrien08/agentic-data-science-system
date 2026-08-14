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

    frontend/src/lib/demo-static/index.json      GET /v1/demos
    frontend/src/lib/demo-static/{slug}.json     GET /v1/demos/{slug}
    frontend/src/lib/demo-static/artifacts.json  slug -> artifact id -> public href
    frontend/public/demo-data/{slug}/artifacts/{id}/{filename}   blob bytes

Run against the database holding the published demos (local ``.env`` by default). Operator
script: reads the DB and writes into the working tree, never the reverse.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from uuid import UUID

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from backend.config.settings import get_settings  # noqa: E402
from backend.db.session import SessionLocal  # noqa: E402
from backend.models.artifact import Artifact  # noqa: E402
from backend.schemas.investigation import build_detail, build_summary  # noqa: E402
from backend.services.demo_publication_service import list_published  # noqa: E402
from backend.storage.resolver import open_reader  # noqa: E402

STATIC_DIR = REPO_ROOT / "frontend" / "src" / "lib" / "demo-static"
BLOB_DIR = REPO_ROOT / "frontend" / "public" / "demo-data"

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


def build_export() -> tuple[dict[str, str], int]:
    """Render every file of the export as {relative path: content}; blobs counted separately."""
    settings = get_settings()
    text_files: dict[str, str] = {}
    blob_bytes = 0

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

            hrefs: dict[str, str] = {}
            for experiment in detail.experiments:
                for ref in experiment.artifacts:
                    artifact = db.get(Artifact, UUID(str(ref.id)))
                    if artifact is None or artifact.blob_deleted_at is not None:
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

        text_files["src/lib/demo-static/artifacts.json"] = _dump(artifact_hrefs)
        text_files["src/lib/demo-static/generated.ts"] = _generated_ts(
            [row.demo_slug for row in rows]
        )

    return text_files, blob_bytes


def _generated_ts(slugs: list[str]) -> str:
    """
    Typed entry point over the exported JSON.

    Generated rather than hand-written so adding or renaming a published demo cannot leave a
    dangling import — the slug list and the import list come from the same query.
    """
    imports = "\n".join(
        f'import detail{i} from "./{slug}.json";' for i, slug in enumerate(slugs)
    )
    entries = ",\n".join(
        f'  "{slug}": detail{i} as unknown as InvestigationDetail' for i, slug in enumerate(slugs)
    )
    return f"""// Generated by scripts/export_demo_static.py — do not edit by hand.
import type {{ InvestigationDetail, InvestigationSummary }} from "@/lib/api/types";

import artifactHrefs from "./artifacts.json";
import index from "./index.json";
{imports}

export const DEMO_INDEX = index as unknown as InvestigationSummary[];

export const DEMO_DETAILS: Record<string, InvestigationDetail> = {{
{entries},
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
    args = parser.parse_args(argv)

    text_files, blob_bytes = build_export()

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
