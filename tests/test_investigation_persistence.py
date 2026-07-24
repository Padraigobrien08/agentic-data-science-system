"""
Unit tests for generalized investigation persistence (in-memory SQLite).

Covers: create + normalized projection, append-only event log, durable
checkpoints, exact-state resume, optimistic concurrency (explicit + StaleData),
idempotent experiment recording, foreign-key integrity, artifact linkage,
reproducibility / tool-version / prompt-model persistence, and legacy-run import.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.exc import StaleDataError

import backend.models  # noqa: F401 — register ORM metadata
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind
from backend.models.enums_investigation import InvestigationOrigin
from backend.models.investigation import Investigation, OrchestrationCheckpoint
from backend.models.investigation_entities import (
    EvidenceArtifactLink,
    EvidenceHypothesisLink,
    ExperimentResultRow,
    HypothesisRow,
)
from backend.models.project import Project
from backend.models.user import User
from backend.repositories.investigation_repository import (
    InvestigationConcurrencyError,
    SqlAlchemyInvestigationRepository,
)
from agentic.domain import (
    ExperimentResult,
    ExperimentStatus,
    HypothesisStatus,
    InvestigationStatus,
    ModelConfigSnapshot,
    Provenance,
    ProvenanceSource,
    ReproducibilityManifest,
)
from agentic.domain.examples import example_inconclusive_investigation, example_investigation


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


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _tool_prov() -> Provenance:
    return Provenance(source=ProvenanceSource.deterministic_tool, tool_name="detect_outliers", tool_version="1.0")


# --- create + normalized projection ----------------------------------------


def test_create_persists_root_and_children(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    inv = example_investigation()
    row = repo.create(inv)
    session.commit()

    assert row.domain_id == inv.id
    assert row.status == inv.status.value
    assert row.origin is InvestigationOrigin.native
    assert len(row.hypotheses) == 1
    assert len(row.evidence) == 1
    assert len(row.datasets) == 1
    assert row.current_conclusion_id is not None
    # append-only event log + a checkpoint were written
    assert len(repo.list_events(row.id)) == 1
    assert len(row.checkpoints) == 1
    # evidence↔hypothesis link created (FK integrity, rebuildable arrays)
    links = session.scalars(select(EvidenceHypothesisLink)).all()
    assert len(links) == 1
    assert links[0].direction == "supports"


def test_reproducibility_and_versions_persisted(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    inv = example_investigation()
    inv.reproducibility = ReproducibilityManifest(
        code_version="abc123",
        tool_versions={"detect_outliers": "1.0"},
        prompt_versions={"planner": "3"},
        model_config_snapshot=ModelConfigSnapshot(provider="openai", model_name="gpt-x", temperature=0.0),
        random_seed=7,
    )
    row = repo.create(inv)
    session.commit()
    assert row.reproducibility_manifest_id is not None
    from backend.models.investigation import ReproducibilityManifestRow

    repro = session.get(ReproducibilityManifestRow, row.reproducibility_manifest_id)
    assert repro.tool_versions_json == {"detect_outliers": "1.0"}
    assert repro.prompt_versions_json == {"planner": "3"}
    assert repro.model_config_json["model_name"] == "gpt-x"
    assert repro.random_seed == 7


# --- exact resume -----------------------------------------------------------


def test_resume_restores_exact_state(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    inv = example_investigation()
    row = repo.create(inv)
    session.commit()

    restored = repo.load_domain(row.id)
    assert restored.model_dump(mode="json") == inv.model_dump(mode="json")


def test_latest_checkpoint_used_for_resume(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    inv = example_investigation()
    row = repo.create(inv)
    session.commit()

    # mutate + save; resume must reflect the newest checkpoint
    inv2 = repo.load_domain(row.id)
    inv2.state.confidence = 0.99
    repo.save_state(row.id, inv2, label="second")
    session.commit()

    checkpoints = session.scalars(
        select(OrchestrationCheckpoint).where(OrchestrationCheckpoint.investigation_id == row.id)
        .order_by(OrchestrationCheckpoint.sequence)
    ).all()
    assert [c.sequence for c in checkpoints] == [0, 1]
    assert repo.load_domain(row.id).state.confidence == 0.99


# --- optimistic concurrency -------------------------------------------------


def test_save_state_bumps_version_each_time(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(example_investigation())
    session.commit()
    v0 = row.state_version
    inv = repo.load_domain(row.id)
    repo.save_state(row.id, inv)
    session.commit()
    assert repo.get(row.id).state_version == v0 + 1


def test_explicit_stale_version_rejected(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(example_investigation())
    session.commit()
    inv = repo.load_domain(row.id)
    with pytest.raises(InvestigationConcurrencyError):
        repo.save_state(row.id, inv, expected_state_version=row.state_version - 1)


def test_concurrent_update_raises_stale_data(factory: sessionmaker[Session]) -> None:
    s1 = factory()
    repo1 = SqlAlchemyInvestigationRepository(s1)
    row = repo1.create(example_investigation())
    s1.commit()
    inv_id = row.id
    s1.close()

    # two sessions load the same row, both mutate the parent, both flush
    sa, sb = factory(), factory()
    a = sa.get(Investigation, inv_id)
    b = sb.get(Investigation, inv_id)
    a.status = "running"
    sa.commit()
    b.status = "failed"
    with pytest.raises(StaleDataError):
        sb.commit()
    sa.close()
    sb.close()


# --- idempotent experiment recording ---------------------------------------


def test_experiment_result_recording_is_idempotent(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(example_investigation())
    session.commit()
    result = ExperimentResult(
        request_id="req_1", tool_name="detect_outliers", status=ExperimentStatus.succeeded,
        metrics={"outlier_count": 2.0}, provenance=_tool_prov(),
    )
    r1, created1 = repo.record_experiment_result(row.id, result=result, idempotency_key="out_fp_1")
    session.commit()
    r2, created2 = repo.record_experiment_result(row.id, result=result, idempotency_key="out_fp_1")
    session.commit()

    assert created1 is True and created2 is False
    assert r1.id == r2.id
    # exactly one row for that key
    rows = session.scalars(
        select(ExperimentResultRow).where(ExperimentResultRow.idempotency_key == "out_fp_1")
    ).all()
    assert len(rows) == 1


def test_experiment_result_records_observations(session: Session) -> None:
    from agentic.domain import Observation

    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(example_investigation())
    session.commit()
    result = ExperimentResult(
        request_id="req_2", tool_name="detect_outliers", status=ExperimentStatus.succeeded,
        observations=[Observation(statement="row 3 is an outlier", provenance=_tool_prov())],
        provenance=_tool_prov(),
    )
    res_row, _ = repo.record_experiment_result(row.id, result=result, idempotency_key="out_fp_2")
    session.commit()
    from backend.models.investigation_entities import ObservationRow

    obs = session.scalars(
        select(ObservationRow).where(ObservationRow.experiment_result_id == res_row.id)
    ).all()
    assert len(obs) == 1


# --- artifact linkage + FK integrity ---------------------------------------


def test_evidence_links_to_existing_artifact(session: Session) -> None:
    user = User(email="a@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.flush()
    run = AnalysisRun(project_id=project.id, status=AnalysisRunStatus.success)
    session.add(run)
    session.flush()
    artifact = Artifact(analysis_run_id=run.id, role_key="anomalies_csv", kind=ArtifactKind.tabular,
                        storage_uri="file:///x.csv")
    session.add(artifact)
    session.flush()

    repo = SqlAlchemyInvestigationRepository(session)
    inv_row = repo.create(example_investigation(), project_id=project.id)
    session.flush()
    evidence_row = inv_row.evidence[0]
    link = repo.link_evidence_artifact(evidence_row.id, artifact.id)
    session.commit()

    assert link.artifact_id == artifact.id
    stored = session.scalars(select(EvidenceArtifactLink)).all()
    assert len(stored) == 1 and stored[0].evidence_id == evidence_row.id


def test_hypothesis_parent_and_status_fk_intact(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(example_investigation())
    session.commit()
    hyp = session.scalars(select(HypothesisRow).where(HypothesisRow.investigation_id == row.id)).one()
    assert hyp.status == HypothesisStatus.supported.value
    assert hyp.investigation_id == row.id


# --- legacy compatibility ---------------------------------------------------


def test_import_legacy_run(session: Session) -> None:
    user = User(email="leg@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="legacy")
    session.add(project)
    session.flush()
    run = AnalysisRun(
        project_id=project.id, initiated_by_user_id=user.id, status=AnalysisRunStatus.success,
        orchestration_goal_text="find unusual revenue changes",
        input_payload_json={"tickers": ["AAPL", "MSFT"], "analysis_goal": "find unusual revenue changes"},
        output_payload_json={"message": "Analysis complete"},
    )
    session.add(run)
    session.flush()

    repo = SqlAlchemyInvestigationRepository(session)
    inv_row = repo.import_legacy_run(run)
    session.commit()

    assert inv_row.origin is InvestigationOrigin.legacy_import
    assert inv_row.analysis_run_id == run.id  # links to the run (still source of truth)
    assert inv_row.status == InvestigationStatus.converged.value
    assert len(inv_row.datasets) == 1
    # re-import is idempotent (unique analysis_run_id)
    again = repo.import_legacy_run(run)
    assert again.id == inv_row.id
    # the original run row is untouched (not removed)
    assert session.get(AnalysisRun, run.id) is not None
    # and the imported investigation restores as a domain object
    restored = repo.load_domain(inv_row.id)
    assert restored.status is InvestigationStatus.converged


def test_inconclusive_example_persists_and_resumes(session: Session) -> None:
    repo = SqlAlchemyInvestigationRepository(session)
    inv = example_inconclusive_investigation()
    row = repo.create(inv)
    session.commit()
    assert row.status == InvestigationStatus.exhausted.value
    restored = repo.load_domain(row.id)
    assert restored.state.termination.reason.value == "insufficient_evidence"
