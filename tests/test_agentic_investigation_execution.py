"""
Wire-up tests for the flag-gated agentic investigation execution path.

Covers engine selection (default EDGAR unless flag on AND run opts in), a full
end-to-end run of the adaptive loop over an in-memory dataset persisted through the
durable investigation store, terminal status mapping, the compact output summary, and
the executable-status / worker guards. All offline and deterministic (fixture policy).
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — register ORM metadata
from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.domain import InvestigationStatus
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus
from backend.models.investigation import Investigation as InvestigationRow
from backend.models.investigation import OrchestrationCheckpoint
from backend.models.investigation_entities import ExperimentResultArtifactLink
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.investigation import build_detail
from backend.services.agentic_investigation_execution_service import (
    AgenticInvestigationExecutionService,
    ENGINE_AGENTIC,
    ENGINE_EDGAR,
    select_run_engine,
)
from backend.services.artifact_service import ArtifactService


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    s = factory()
    try:
        yield s
    finally:
        s.close()


def _records() -> list[dict]:
    return [{"entity": "A", "period": f"2021-{i}", "revenue": 5 + 6 * i} for i in range(8)]


def _agentic_payload(**overrides) -> dict:
    payload = {
        "engine": ENGINE_AGENTIC,
        "analysis_goal": "revenue is increasing over time",
        "dataset": {
            "adapter": "in_memory",
            "name": "rev",
            "records": _records(),
            "time_field": "period",
            "entity_id_fields": ["entity"],
        },
    }
    payload.update(overrides)
    return payload


def _seed_run(
    session: Session,
    *,
    input_payload: dict | None,
    status: AnalysisRunStatus = AnalysisRunStatus.pending,
) -> AnalysisRun:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.flush()
    run = AnalysisRun(
        project_id=project.id,
        initiated_by_user_id=user.id,
        status=status,
        input_payload_json=input_payload,
    )
    session.add(run)
    session.commit()
    return run


def _fixture_service(session: Session) -> AgenticInvestigationExecutionService:
    return AgenticInvestigationExecutionService(session, policy_factory=lambda s: FixtureAgentPolicy())


# --- engine selection -------------------------------------------------------


def test_flag_off_always_selects_edgar(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())
    assert select_run_engine(run, Settings(agentic_engine_enabled=False)) == ENGINE_EDGAR


def test_flag_on_with_optin_selects_agentic(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())
    assert select_run_engine(run, Settings(agentic_engine_enabled=True)) == ENGINE_AGENTIC


def test_flag_on_without_optin_selects_edgar(session: Session) -> None:
    run = _seed_run(session, input_payload={"tickers": ["AAPL"]})
    assert select_run_engine(run, Settings(agentic_engine_enabled=True)) == ENGINE_EDGAR


def test_flag_on_missing_payload_selects_edgar(session: Session) -> None:
    run = _seed_run(session, input_payload=None)
    assert select_run_engine(run, Settings(agentic_engine_enabled=True)) == ENGINE_EDGAR


# --- end-to-end execution ---------------------------------------------------


def test_execute_runs_loop_and_persists_investigation(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())

    result = _fixture_service(session).execute_analysis_run(run.id)

    # terminal, non-failed outcome mapped onto an analysis-run status
    assert result.investigation_status in (InvestigationStatus.converged, InvestigationStatus.exhausted)
    assert result.db_status in (AnalysisRunStatus.success, AnalysisRunStatus.partial_success)

    session.expire_all()
    reloaded = session.get(AnalysisRun, run.id)
    assert reloaded.status == result.db_status

    # compact summary persisted for the read-API / UI
    out = reloaded.output_payload_json
    assert out["engine"] == ENGINE_AGENTIC
    assert out["investigation_id"] == str(run.id)
    assert out["dataset"]["adapter_id"] == "in_memory"
    assert out["counts"]["hypotheses"] >= 1

    # a durable investigation was created, linked to the run/project/user, with checkpoints
    inv_row = session.scalar(select(InvestigationRow).where(InvestigationRow.domain_id == str(run.id)))
    assert inv_row is not None
    assert inv_row.analysis_run_id == run.id
    assert inv_row.project_id == run.project_id
    assert inv_row.initiated_by_user_id == run.initiated_by_user_id
    checkpoints = session.scalars(
        select(OrchestrationCheckpoint).where(OrchestrationCheckpoint.investigation_id == inv_row.id)
    ).all()
    assert len(checkpoints) >= 1


def test_execute_records_experiments_over_the_frame(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload())
    result = _fixture_service(session).execute_analysis_run(run.id)
    # the loop actually ran deterministic experiments over the materialized frame
    assert result.experiments_count >= 1


def _sample_total(metric, suffix: str) -> float:
    """Sum all label children of a prometheus metric via the public collect() API."""
    total = 0.0
    for family in metric.collect():
        for s in family.samples:
            if s.name.endswith(suffix):
                total += s.value
    return total


def test_execute_emits_agentic_metrics(session: Session, tmp_path) -> None:
    """A terminal agentic run increments the agentic metrics and the shared run-terminal counter."""
    from backend.observability import metrics as m

    before_terminal = _sample_total(m.AGENTIC_INVESTIGATION_TERMINAL_TOTAL, "_total")
    before_duration = _sample_total(m.AGENTIC_INVESTIGATION_DURATION_SECONDS, "_count")
    before_experiments = _sample_total(m.AGENTIC_EXPERIMENTS_TOTAL, "_total")
    before_run_terminal = _sample_total(m.ANALYSIS_RUN_TERMINAL_TOTAL, "_total")

    run = _seed_run(session, input_payload=_agentic_payload())
    _fixture_service(session).execute_analysis_run(run.id)

    assert _sample_total(m.AGENTIC_INVESTIGATION_TERMINAL_TOTAL, "_total") == before_terminal + 1
    assert _sample_total(m.AGENTIC_INVESTIGATION_DURATION_SECONDS, "_count") == before_duration + 1
    assert _sample_total(m.AGENTIC_EXPERIMENTS_TOTAL, "_total") >= before_experiments + 1
    # agentic runs also show up in the engine-agnostic run-terminal metric
    assert _sample_total(m.ANALYSIS_RUN_TERMINAL_TOTAL, "_total") == before_run_terminal + 1


def test_execute_ingests_and_links_experiment_artifacts(session: Session, tmp_path) -> None:
    """Artifacts emitted by experiments are ingested into the artifacts table, linked to their
    result, and surfaced (downloadable) through the read-API detail projection."""
    run = _seed_run(session, input_payload=_agentic_payload())
    artifact_service = ArtifactService(session, settings=Settings(artifact_storage_root=tmp_path / "blobs"))
    service = AgenticInvestigationExecutionService(
        session, policy_factory=lambda s: FixtureAgentPolicy(), artifact_service=artifact_service
    )

    service.execute_analysis_run(run.id)
    session.expire_all()

    # artifact rows were created and scoped to the run
    artifacts = session.scalars(select(Artifact).where(Artifact.analysis_run_id == run.id)).all()
    assert artifacts, "expected experiments to emit at least one ingested artifact"
    for a in artifacts:
        assert a.byte_size and a.byte_size > 0
        assert (a.meta_json or {}).get("source") == "agentic_experiment"
        # bytes are actually retrievable from the object store
        assert len(artifact_service.load_bytes(a.id)) == a.byte_size

    # each artifact is linked to an experiment result (experiment -> artifact linkage)
    links = session.scalars(select(ExperimentResultArtifactLink)).all()
    linked_ids = {link.artifact_id for link in links}
    assert linked_ids == {a.id for a in artifacts}

    # the read-API surfaces artifacts under the experiments that produced them
    inv_row = session.scalar(select(InvestigationRow).where(InvestigationRow.domain_id == str(run.id)))
    detail = build_detail(inv_row)
    surfaced = [ref for x in detail.experiments for ref in x.artifacts]
    assert {ref.id for ref in surfaced} == {a.id for a in artifacts}
    assert all(ref.name and ref.kind for ref in surfaced)


def test_artifact_ingestion_is_idempotent(session: Session, tmp_path) -> None:
    """Re-running ingestion against already-linked results never duplicates artifacts or links."""
    from agentic.domain import Investigation as DomainInvestigation
    from agentic.experiments import InMemoryArtifactSink
    from agentic.experiments.artifacts import ArtifactRecord
    from agentic.experiments.descriptor import ArtifactType

    run = _seed_run(session, input_payload=_agentic_payload())
    artifact_service = ArtifactService(session, settings=Settings(artifact_storage_root=tmp_path / "blobs"))
    service = AgenticInvestigationExecutionService(
        session, policy_factory=lambda s: FixtureAgentPolicy(), artifact_service=artifact_service
    )
    service.execute_analysis_run(run.id)
    session.expire_all()
    first = session.scalars(select(Artifact).where(Artifact.analysis_run_id == run.id)).all()

    # Rebuild a sink whose records match the persisted results' artifact ids, then re-ingest.
    # The result rows already carry links, so the guard must skip them (no duplicate rows/links).
    inv_row = session.scalar(select(InvestigationRow).where(InvestigationRow.domain_id == str(run.id)))
    reloaded = DomainInvestigation.model_validate(
        max(inv_row.checkpoints, key=lambda c: c.sequence).state_json
    )
    replay = InMemoryArtifactSink()
    for result in [*reloaded.state.completed_experiments, *reloaded.state.failed_experiments]:
        for art_id in result.artifact_ids:
            replay.records.append(
                ArtifactRecord(
                    id=art_id, name="replay", artifact_type=ArtifactType.json,
                    media_type="application/json", fingerprint="sha256:replay", byte_size=2,
                )
            )
            replay.contents[art_id] = b"{}"
    assert replay.records, "expected the reproduced run to reference artifact ids"

    service._ingest_artifacts(run.id, reloaded, replay)
    session.flush()
    session.expire_all()

    second = session.scalars(select(Artifact).where(Artifact.analysis_run_id == run.id)).all()
    assert {a.id for a in second} == {a.id for a in first}
    links = session.scalars(select(ExperimentResultArtifactLink)).all()
    assert len(links) == len(first)


# --- guards -----------------------------------------------------------------


def test_running_status_is_not_executable(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload(), status=AnalysisRunStatus.running)
    with pytest.raises(ValueError, match="already executing"):
        _fixture_service(session).execute_analysis_run(run.id)


def test_worker_execution_requires_queued(session: Session) -> None:
    run = _seed_run(session, input_payload=_agentic_payload(), status=AnalysisRunStatus.pending)
    with pytest.raises(ValueError, match="requires status 'queued'"):
        _fixture_service(session).execute_analysis_run(run.id, from_worker=True)
