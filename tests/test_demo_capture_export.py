"""
The demo capture bundle and the export's refusal to publish a degraded replay.

A recorded run costs real money and retention destroys its expensive parts on a timer
(model payloads at 30 days, artifact blobs at 180). These tests pin the two behaviours that
protect that spend: everything expensive is captured, and an export that would silently ship
a hollow demo fails instead.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401  — register mappers
from backend.config.settings import get_settings
from backend.db.base import Base
from backend.llm.pricing import parse_model_prices
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind, ModelCallStatus
from backend.models.investigation import Investigation
from backend.models.investigation_entities import (
    ExperimentResultArtifactLink,
    ExperimentResultRow,
)
from backend.models.model_call import ModelCall
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.demo_capture import build_demo_capture

NOW = datetime(2026, 8, 19, 12, 0, tzinfo=timezone.utc)


# ------------------------------------------------------------------ pure builder


@dataclass
class _Call:
    """Duck-typed stand-in for a ModelCall row; the builder takes rows, not a session."""

    id: uuid.UUID = field(default_factory=uuid.uuid4)
    provider: str = "openai"
    model_name: str = "gpt-5.4-mini"
    prompt_id: str | None = "interpret_goal"
    prompt_version: str | None = "v3"
    status: Any = "succeeded"
    prompt_tokens: int | None = 100
    completion_tokens: int | None = 50
    latency_ms: int | None = 400
    request_payload_json: Any = None
    response_payload_json: Any = None
    error_detail: str | None = None
    started_at: datetime | None = NOW
    created_at: datetime = NOW
    payloads_redacted_at: datetime | None = None
    finished_at: datetime | None = None


def _capture(calls, conversations=(), prices=None):
    return build_demo_capture(
        demo_slug="a-demo",
        investigation_id=uuid.uuid4(),
        analysis_run_id=uuid.uuid4(),
        model_call_rows=list(calls),
        conversation_rows=list(conversations),
        prices=prices,
    )


def test_capture_preserves_payloads_and_orders_calls_chronologically() -> None:
    second = _Call(started_at=NOW + timedelta(seconds=5), request_payload_json={"n": 2})
    first = _Call(started_at=NOW, request_payload_json={"n": 1}, response_payload_json={"ok": True})

    capture = _capture([second, first])

    assert [c.sequence for c in capture.model_calls] == [0, 1]
    assert capture.model_calls[0].request_payload_json == {"n": 1}
    # The payloads are the whole point of the bundle — they must survive the round trip.
    assert capture.model_calls[0].response_payload_json == {"ok": True}
    assert capture.model_calls[1].request_payload_json == {"n": 2}


def test_capture_totals_sum_tokens_and_latency() -> None:
    capture = _capture([_Call(), _Call(prompt_tokens=20, completion_tokens=5, latency_ms=100)])

    assert capture.totals.model_calls == 2
    assert capture.totals.prompt_tokens == 120
    assert capture.totals.completion_tokens == 55
    assert capture.totals.total_tokens == 175
    assert capture.totals.latency_ms == 500


def test_capture_reports_cost_unknown_rather_than_zero_when_unpriced() -> None:
    """An unconfigured price table must not read as a free run."""
    capture = _capture([_Call()], prices=None)

    assert capture.totals.priced is False
    assert capture.totals.est_cost_usd == 0.0
    assert capture.model_calls[0].est_cost_usd is None


def test_capture_prices_calls_when_a_price_table_exists() -> None:
    prices = parse_model_prices({"gpt-5.4-mini": {"input_per_1m": 2.0, "output_per_1m": 8.0}})
    assert prices, "price table should parse from a plain dict"

    # 1M prompt tokens at $2/M + 500k completion at $8/M = $2 + $4.
    capture = _capture([_Call(prompt_tokens=1_000_000, completion_tokens=500_000)], prices=prices)

    assert capture.totals.priced is True
    assert capture.totals.est_cost_usd == pytest.approx(6.0)
    assert capture.model_calls[0].est_cost_usd == pytest.approx(6.0)


def test_capture_tolerates_missing_token_counts() -> None:
    capture = _capture([_Call(prompt_tokens=None, completion_tokens=None, latency_ms=None)])

    assert capture.totals.total_tokens == 0
    assert capture.totals.model_calls == 1


def test_capture_includes_chat_threads_in_message_order() -> None:
    convo = type(
        "C",
        (),
        {
            "id": uuid.uuid4(),
            "title": "Margin vs growth",
            "created_at": NOW,
            "messages": [
                type("M", (), {"id": uuid.uuid4(), "role": "assistant", "status": "complete",
                               "content": "second", "analysis_run_id": None,
                               "created_at": NOW + timedelta(seconds=1)})(),
                type("M", (), {"id": uuid.uuid4(), "role": "user", "status": "complete",
                               "content": "first", "analysis_run_id": None, "created_at": NOW})(),
            ],
        },
    )()

    capture = _capture([], conversations=[convo])

    assert [m.content for m in capture.chat[0].messages] == ["first", "second"]
    assert capture.chat[0].title == "Margin vs growth"


# ------------------------------------------------------------------ export guards


@pytest.fixture
def exporting(tmp_path, monkeypatch: pytest.MonkeyPatch) -> Iterator[tuple[Any, sessionmaker]]:
    """The export module bound to a throwaway SQLite database and blob root."""
    monkeypatch.setenv("EDGAR_BACKEND_ARTIFACT_STORAGE_ROOT", str(tmp_path / "blobs"))
    monkeypatch.setenv("EDGAR_BACKEND_JWT_SECRET", "x" * 40)
    monkeypatch.setenv("EDGAR_BACKEND_OPS_API_TOKEN", "ops")
    get_settings.cache_clear()

    import scripts.export_demo_static as export_module

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    monkeypatch.setattr(export_module, "SessionLocal", factory)
    # Keep the export from writing blobs into the repo working tree during tests.
    monkeypatch.setattr(export_module, "REPO_ROOT", tmp_path)
    yield export_module, factory
    get_settings.cache_clear()


def _seed_published(factory: sessionmaker, *, redacted: bool = False, with_artifact: bool = False,
                    blob_pruned: bool = False) -> None:
    storage_root = get_settings().artifact_storage_root
    storage_root.mkdir(parents=True, exist_ok=True)
    key = f"{uuid.uuid4().hex}.md"
    (storage_root / key).write_text("# Recorded finding\n", encoding="utf-8")

    with factory() as db:
        user = User(email=f"o-{uuid.uuid4().hex[:8]}@example.com")
        db.add(user)
        db.flush()
        project = Project(owner_user_id=user.id, name="Demo project")
        db.add(project)
        db.flush()
        run = AnalysisRun(project_id=project.id, initiated_by_user_id=user.id,
                          status=AnalysisRunStatus.success)
        db.add(run)
        db.flush()
        investigation = Investigation(
            domain_id=f"inv_{uuid.uuid4().hex[:10]}", project_id=project.id,
            initiated_by_user_id=user.id, analysis_run_id=run.id,
            status="concluded", demo_slug="a-demo",
        )
        db.add(investigation)
        db.flush()

        db.add(ModelCall(
            analysis_run_id=run.id, provider="openai", model_name="gpt-5.4-mini",
            status=ModelCallStatus.success, prompt_tokens=10, completion_tokens=5,
            request_payload_json=None if redacted else {"messages": []},
            response_payload_json=None if redacted else {"choices": []},
            payloads_redacted_at=NOW if redacted else None,
        ))

        if with_artifact:
            artifact = Artifact(
                analysis_run_id=run.id, kind=ArtifactKind.document, role_key="finding_md",
                storage_uri=f"local:{key}", mime_type="text/markdown",
                byte_size=(storage_root / key).stat().st_size,
                blob_deleted_at=NOW if blob_pruned else None,
            )
            db.add(artifact)
            db.flush()
            experiment = ExperimentResultRow(
                investigation_id=investigation.id, domain_id=f"exp_{uuid.uuid4().hex[:8]}",
                tool_name="summarize_distribution", status="succeeded",
                idempotency_key=uuid.uuid4().hex,
            )
            db.add(experiment)
            db.flush()
            db.add(ExperimentResultArtifactLink(
                experiment_result_id=experiment.id, artifact_id=artifact.id
            ))
        db.commit()


def test_export_refuses_when_model_payloads_were_already_redacted(exporting) -> None:
    export_module, factory = exporting
    _seed_published(factory, redacted=True)

    with pytest.raises(SystemExit) as excinfo:
        export_module.build_export()

    message = str(excinfo.value)
    assert "redacted" in message
    # The message has to name the fix, since by this point the content is unrecoverable.
    assert "RETENTION_MODEL_PAYLOAD_DAYS" in message


def test_allow_degraded_exports_anyway(exporting, capsys) -> None:
    export_module, factory = exporting
    _seed_published(factory, redacted=True)

    text_files, _ = export_module.build_export(allow_degraded=True)

    assert "src/lib/demo-static/a-demo.capture.json" in text_files
    assert "WARNING" in capsys.readouterr().out


def test_export_refuses_when_an_artifact_blob_was_pruned(exporting) -> None:
    export_module, factory = exporting
    _seed_published(factory, with_artifact=True, blob_pruned=True)

    with pytest.raises(SystemExit) as excinfo:
        export_module.build_export()

    assert "pruned" in str(excinfo.value)


def test_orphaned_blobs_from_a_previous_publish_are_pruned(exporting, tmp_path) -> None:
    """
    Artifact ids are per-run, so re-publishing a slug strands the previous run's blobs.

    Nothing removed them, so every re-publish left a full set of dead files behind, committed
    and served forever. Two rounds of that were cleaned up by hand before this existed.
    """
    export_module, factory = exporting
    _seed_published(factory, with_artifact=True)

    root = tmp_path / "frontend" / "public" / "demo-data" / "a-demo" / "artifacts"
    stale = root / "0f4717bb-df7d-4de4-83dd-cf18f96179cc"
    stale.mkdir(parents=True)
    (stale / "coefficients.csv").write_text("old,run\n", encoding="utf-8")

    export_module.build_export()

    assert not stale.exists()
    # The blobs this export actually wrote survive.
    assert any(p.is_dir() for p in root.iterdir())


def test_pruning_leaves_directories_the_exporter_did_not_write(exporting, tmp_path) -> None:
    """Scoped to artifact-id-shaped names so it cannot delete something put there by hand."""
    export_module, factory = exporting
    _seed_published(factory, with_artifact=True)

    root = tmp_path / "frontend" / "public" / "demo-data" / "a-demo" / "artifacts"
    root.mkdir(parents=True, exist_ok=True)
    hand_written = root / "README-notes"
    hand_written.mkdir()

    export_module.build_export()

    assert hand_written.exists()


def test_check_mode_never_deletes(exporting, tmp_path) -> None:
    """`--check` is a read-only verification; it must not prune as a side effect."""
    export_module, factory = exporting
    _seed_published(factory, with_artifact=True)

    root = tmp_path / "frontend" / "public" / "demo-data" / "a-demo" / "artifacts"
    stale = root / "0f4717bb-df7d-4de4-83dd-cf18f96179cc"
    stale.mkdir(parents=True)

    export_module.build_export(prune=False)

    assert stale.exists()


def test_healthy_export_emits_a_capture_bundle_alongside_the_detail(exporting) -> None:
    export_module, factory = exporting
    _seed_published(factory, with_artifact=True)

    text_files, _ = export_module.build_export()

    assert "src/lib/demo-static/a-demo.json" in text_files
    capture = text_files["src/lib/demo-static/a-demo.capture.json"]
    assert '"model_calls"' in capture
    # generated.ts must import the capture or the frontend cannot reach it.
    assert "a-demo.capture.json" in text_files["src/lib/demo-static/generated.ts"]
