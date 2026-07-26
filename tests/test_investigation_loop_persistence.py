"""
Integration: run the adaptive loop persisting to the durable store (SQLite).

Confirms every decision is persisted to the investigation tables and that a
checkpointed run resumes from the database to the same subsequent state.
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
from backend.models.investigation_entities import AgentDecisionRow
from backend.services.investigation_store import SqlAlchemyInvestigationStore


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _df() -> pd.DataFrame:
    return pd.DataFrame({"entity": ["A"] * 8, "period": [f"2021-{i}" for i in range(8)],
                         "revenue": [5 + 6 * i for i in range(8)]})


def _manifest(df):
    return InMemoryDatasetAdapter(frame=df, time_field="period", entity_id_fields=["entity"],
                                  role_hints={"revenue": ColumnRole.metric}).build_manifest(AdapterRequest())


def test_loop_persists_decisions_and_resumes_from_db(factory: sessionmaker[Session]) -> None:
    df = _df()
    m = _manifest(df)
    goal = "revenue is increasing over time"

    # full run persisted to DB
    s1 = factory()
    inv_full = InvestigationLoop().start(
        goal, manifest=m, frame=df, seed="db-full", store=SqlAlchemyInvestigationStore(s1))
    # decisions were persisted
    decisions = s1.scalars(select(AgentDecisionRow)).all()
    assert len(decisions) == len(inv_full.state.decisions) > 0
    row = s1.scalar(select(InvestigationRow).where(InvestigationRow.domain_id == inv_full.id))
    assert row is not None and row.status == inv_full.status.value
    s1.close()

    # partial run + resume from the database
    s2 = factory()
    store2 = SqlAlchemyInvestigationStore(s2)
    partial = InvestigationLoop().start(goal, manifest=m, frame=df, seed="db-resume",
                                        store=store2, max_new_experiments=1)
    assert partial.state.termination is None
    reloaded = store2.load(partial.id)
    resumed = InvestigationLoop().resume(reloaded, goal_text=goal, manifest=m, frame=df, store=store2)
    s2.close()

    # resuming reproduces the same terminal disposition as an uninterrupted run
    assert resumed.state.current_conclusion.disposition == inv_full.state.current_conclusion.disposition
    assert [d.decision_type.value for d in resumed.state.decisions] == \
           [d.decision_type.value for d in inv_full.state.decisions]
