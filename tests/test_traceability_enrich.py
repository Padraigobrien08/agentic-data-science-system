"""Post-ingest traceability artifact id enrichment."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from backend.agents.traceability_summary import enrich_traceability_artifact_ids
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun as AnalysisRunRow
from backend.models.artifact import Artifact
from backend.models.enums import AnalysisRunStatus, ArtifactKind
from backend.models.project import Project
from backend.models.user import User


@pytest.fixture
def session_with_run_trace() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    u = User(email=f"tr-{uuid.uuid4().hex[:8]}@example.com")
    session.add(u)
    session.flush()
    p = Project(owner_user_id=u.id, name="TrProj")
    session.add(p)
    session.flush()
    arun = AnalysisRunRow(
        project_id=p.id,
        status=AnalysisRunStatus.pending,
        meta_json={
            "ai_agents": {
                "traceability": {
                    "contract_version": "1",
                    "evidence_artifact_refs": [{"role": "panel_csv", "basename": "p.csv"}],
                }
            }
        },
    )
    session.add(arun)
    session.flush()
    art = Artifact(
        analysis_run_id=arun.id,
        role_key="panel_csv",
        kind=ArtifactKind.tabular,
        storage_uri="local:artifacts/analysis_runs/x/p.csv",
        mime_type="text/csv",
        byte_size=1,
        content_sha256="a" * 64,
        meta_json={},
    )
    session.add(art)
    session.flush()
    session._test_arun_id = arun.id  # type: ignore[attr-defined]
    session._test_artifact_id = art.id  # type: ignore[attr-defined]
    return session


def test_enrich_traceability_artifact_ids(session_with_run_trace: Session) -> None:
    aid = session_with_run_trace._test_arun_id  # type: ignore[attr-defined]
    expected_id = str(session_with_run_trace._test_artifact_id)  # type: ignore[attr-defined]
    enrich_traceability_artifact_ids(session_with_run_trace, aid)
    session_with_run_trace.commit()
    row = session_with_run_trace.get(AnalysisRunRow, aid)
    assert row is not None
    tr = (row.meta_json or {}).get("ai_agents", {}).get("traceability", {})
    assert expected_id in tr.get("evidence_artifact_ids", [])
    assert tr.get("evidence_artifacts_by_role", {}).get("panel_csv") == expected_id
