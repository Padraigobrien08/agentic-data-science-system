"""
Integration: the evidence→experiment link survives the whole way to the read model.

``tests/agentic/test_evidence_provenance_link.py`` proves the loop writes the link. That is
necessary and not sufficient — the loop carries *domain* ids (``<seed>-res-N``) while the
column holding the link is a foreign key to ``experiment_results.id``, so the translation
happens at the persistence boundary and can drop it silently. It did: the repository built
evidence rows without ever setting ``experiment_result_id``, and every published demo served
``null``.

This is the assertion that would have caught it, because it checks the bytes a client
actually receives rather than the state the loop holds in memory.
"""

from __future__ import annotations

from collections.abc import Iterator

import pandas as pd
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from agentic.adapters import AdapterRequest, InMemoryDatasetAdapter
from agentic.agent import InvestigationLoop
from agentic.domain.enums import ColumnRole
from backend.db.base import Base
from backend.models.investigation import Investigation as InvestigationRow
from backend.schemas.investigation import build_detail
from backend.services.investigation_store import SqlAlchemyInvestigationStore

GOAL = "Has revenue trended upward over recent periods, or is volatility the explanation?"


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entity": ["A"] * 8,
            "period": [f"2021-{i}" for i in range(8)],
            "revenue": [5 + 6 * i for i in range(8)],
        }
    )


@pytest.fixture
def detail(factory: sessionmaker[Session]):
    df = _df()
    manifest = InMemoryDatasetAdapter(
        frame=df,
        time_field="period",
        entity_id_fields=["entity"],
        role_hints={"revenue": ColumnRole.metric},
    ).build_manifest(AdapterRequest())

    session = factory()
    investigation = InvestigationLoop().start(
        GOAL, manifest=manifest, frame=df, seed="readmodel",
        store=SqlAlchemyInvestigationStore(session),
    )
    row = session.scalar(
        select(InvestigationRow).where(InvestigationRow.domain_id == investigation.id)
    )
    assert row is not None
    yield build_detail(row)
    session.close()


def test_the_read_model_has_evidence_to_check(detail) -> None:
    assert detail.evidence, "no evidence in the read model — the assertions below are vacuous"
    assert detail.experiments


def test_served_evidence_names_its_experiment(detail) -> None:
    """The claim on the README: conclusion → evidence → the experiment that produced it."""
    unlinked = [e.id for e in detail.evidence if not e.experiment_result_id]

    assert not unlinked, (
        "the API is serving evidence that cannot be traced to a computation: " f"{unlinked}"
    )


def test_served_links_resolve_within_the_same_payload(detail) -> None:
    """
    A client holds one ``InvestigationDetail``. Every link it follows must land inside it —
    an id that resolves only against a second request is not a trace, it is a lookup.
    """
    experiment_ids = {x.id for x in detail.experiments}
    dangling = sorted(
        {e.experiment_result_id for e in detail.evidence if e.experiment_result_id}
        - experiment_ids
    )

    assert not dangling, f"evidence points outside the served payload: {dangling}"
