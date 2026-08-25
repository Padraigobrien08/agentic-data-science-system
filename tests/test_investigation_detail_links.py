"""
The links inside an investigation response have to point at things in the same response.

`build_detail` keys every item by its ``domain_id`` — hypotheses, experiments, evidence. The
links *between* them were emitted as database primary keys, so nothing could be joined:
`evidenceForHypothesis` in the frontend matched zero rows on every published demo, and the
trace rendered claims with no supporting evidence instead of failing.

Nothing caught it because the frontend fixtures used the same string on both sides of the
join. These tests use rows whose primary key and domain id differ, which is the only shape
that can catch it.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.models  # noqa: F401  — register mappers
from backend.db.base import Base
from backend.models.analysis_run import AnalysisRun
from backend.models.enums import AnalysisRunStatus
from backend.models.investigation import Investigation
from backend.models.investigation_entities import (
    EvidenceHypothesisLink,
    EvidenceRow,
    ExperimentResultRow,
    HypothesisRow,
)
from backend.models.project import Project
from backend.models.user import User
from backend.schemas.investigation import build_detail


@pytest.fixture
def session() -> Iterator[Session]:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        yield db


def _investigation(db: Session, *, link_experiment: bool) -> Investigation:
    user = User(email=f"o-{uuid.uuid4().hex[:8]}@example.com")
    db.add(user)
    db.flush()
    project = Project(owner_user_id=user.id, name="p")
    db.add(project)
    db.flush()
    run = AnalysisRun(project_id=project.id, initiated_by_user_id=user.id, status=AnalysisRunStatus.success)
    db.add(run)
    db.flush()
    inv = Investigation(
        domain_id="inv-1", project_id=project.id, initiated_by_user_id=user.id,
        analysis_run_id=run.id, status="concluded",
    )
    db.add(inv)
    db.flush()

    # Primary keys are random uuids; domain ids are the readable loop ids. The two spaces
    # differing is the whole point of the fixture.
    hypothesis = HypothesisRow(
        investigation_id=inv.id, domain_id="inv-1-hyp-0",
        statement="staffing explains on-time rate", status="supported",
        confidence=0.95, prior_confidence=0.5,
    )
    experiment = ExperimentResultRow(
        investigation_id=inv.id, domain_id="inv-1-res-0",
        tool_name="analyze_correlation", status="succeeded", idempotency_key=uuid.uuid4().hex,
    )
    db.add_all([hypothesis, experiment])
    db.flush()

    evidence = EvidenceRow(
        investigation_id=inv.id, domain_id="inv-1-evd-0", evidence_type="descriptive_stat",
        claim="r=0.75", direction="supports", strength=0.75, reliability=0.76, coverage=1.0,
        experiment_result_id=experiment.id if link_experiment else None,
    )
    db.add(evidence)
    db.flush()
    db.add(EvidenceHypothesisLink(
        evidence_id=evidence.id, hypothesis_id=hypothesis.id, direction="supports"
    ))
    db.commit()
    db.refresh(inv)
    return inv


def test_evidence_links_resolve_against_the_hypotheses_in_the_same_response(session) -> None:
    """The join the trace depends on: claim -> the evidence that moved it."""
    detail = build_detail(_investigation(session, link_experiment=True))

    hypothesis_ids = {h.id for h in detail.hypotheses}
    linked = {hid for e in detail.evidence for hid in e.hypothesis_ids}

    assert linked, "evidence must expose at least one hypothesis link"
    assert linked <= hypothesis_ids, (
        f"evidence points at {linked}, which is not among the hypotheses {hypothesis_ids}"
    )


def test_evidence_links_resolve_against_the_experiments_in_the_same_response(session) -> None:
    detail = build_detail(_investigation(session, link_experiment=True))

    experiment_ids = {x.id for x in detail.experiments}
    referenced = {e.experiment_result_id for e in detail.evidence if e.experiment_result_id}

    assert referenced, "evidence must expose its experiment link when the FK is set"
    assert referenced <= experiment_ids


def test_links_are_domain_ids_not_database_keys(session) -> None:
    """Names the actual regression, so a future change back is obvious in the failure."""
    detail = build_detail(_investigation(session, link_experiment=True))

    assert detail.evidence[0].hypothesis_ids == ["inv-1-hyp-0"]
    assert detail.evidence[0].experiment_result_id == "inv-1-res-0"


def test_an_absent_experiment_link_stays_absent(session) -> None:
    """A null FK must not become a dangling id."""
    detail = build_detail(_investigation(session, link_experiment=False))

    assert detail.evidence[0].experiment_result_id is None
    # The hypothesis link is unaffected by the missing experiment.
    assert detail.evidence[0].hypothesis_ids == ["inv-1-hyp-0"]
