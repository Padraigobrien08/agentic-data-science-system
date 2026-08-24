"""
Keeping the record of *why* an experiment was run.

An :class:`ExperimentRequest` carries what a result cannot: the claims it was raised to
test, its purpose, and the information gain expected of it. The domain retires a request out
of ``pending_experiments`` the moment its result lands, so persistence that saved only
pending requests dropped every request that actually ran — a live database held 121 results
against 0 requests, and "which experiment tested which claim" was unanswerable.

That link is the spine of a readable trace, so these tests pin it at the two places it can
be lost: the write, and the read that joins it back onto the result.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401 — register ORM metadata
from agentic.domain import (
    ExperimentRequest,
    ExperimentResult,
    ExperimentStatus,
    Provenance,
    ProvenanceSource,
)
from agentic.domain.examples import example_investigation
from backend.db.base import Base
from backend.models.investigation_entities import ExperimentRequestRow
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.schemas.investigation import build_detail


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


def _prov() -> Provenance:
    return Provenance(source=ProvenanceSource.deterministic_tool, tool_name="t", tool_version="1.0")


def _ran_one_experiment():
    """An investigation whose single experiment has completed — so nothing is pending."""
    inv = example_investigation()
    state = inv.state
    hypothesis_id = state.hypotheses[0].id

    request = ExperimentRequest(
        id="exp-0",
        definition_id="analyze_correlation",
        tool_name="analyze_correlation",
        target_hypothesis_ids=[hypothesis_id],
        purpose="test the claim directly",
        provenance=_prov(),
    )
    state.add_experiment_request(request)
    state.record_experiment_result(
        ExperimentResult(
            id="res-0",
            request_id="exp-0",
            tool_name="analyze_correlation",
            status=ExperimentStatus.succeeded,
            provenance=_prov(),
        )
    )
    return inv, hypothesis_id


def test_a_request_that_ran_is_still_written(session: Session) -> None:
    inv, _ = _ran_one_experiment()
    assert inv.state.pending_experiments == []  # the condition that used to lose it

    SqlAlchemyInvestigationRepository(session).create(inv)
    session.commit()

    # The example fixture ships a still-pending request too; the one that matters here is
    # the executed one, which is precisely what used to be missing.
    saved = {r.domain_id for r in session.query(ExperimentRequestRow).all()}
    assert "exp-0" in saved


def test_the_claims_it_was_raised_to_test_survive(session: Session) -> None:
    inv, hypothesis_id = _ran_one_experiment()

    SqlAlchemyInvestigationRepository(session).create(inv)
    session.commit()

    row = session.query(ExperimentRequestRow).filter_by(domain_id="exp-0").one()
    assert row.target_hypothesis_ids_json == [hypothesis_id]
    assert row.purpose == "test the claim directly"


def test_the_read_api_joins_the_targets_back_onto_the_result(session: Session) -> None:
    inv, hypothesis_id = _ran_one_experiment()
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(inv)
    session.commit()
    session.refresh(row)

    detail = build_detail(row)

    experiment = next(x for x in detail.experiments if x.request_domain_id == "exp-0")
    assert experiment.target_hypothesis_ids == [hypothesis_id]
    # Same id space as the claims themselves, or the join is unusable to a reader.
    assert hypothesis_id in {h.id for h in detail.hypotheses}


def test_an_experiment_with_no_recorded_request_reports_empty_not_wrong(session: Session) -> None:
    # Every run before this fix looks like this. Empty must read as "unknown", never as
    # "this experiment tested nothing".
    inv = example_investigation()
    inv.state.record_experiment_result(
        ExperimentResult(
            id="res-orphan",
            request_id="exp-missing",
            tool_name="analyze_correlation",
            status=ExperimentStatus.succeeded,
            provenance=_prov(),
        )
    )
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(inv)
    session.commit()
    session.refresh(row)

    detail = build_detail(row)

    orphan = next(x for x in detail.experiments if x.request_domain_id == "exp-missing")
    assert orphan.target_hypothesis_ids == []


def test_saving_twice_does_not_duplicate_the_request(session: Session) -> None:
    inv, _ = _ran_one_experiment()
    repo = SqlAlchemyInvestigationRepository(session)
    row = repo.create(inv)
    session.commit()

    repo.save_state(row.id, inv)
    session.commit()

    executed = session.query(ExperimentRequestRow).filter_by(domain_id="exp-0").all()
    assert len(executed) == 1
