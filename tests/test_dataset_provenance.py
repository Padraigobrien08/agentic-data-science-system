"""
What a published run says about the data it analysed.

Three separate defects met here, and all three were invisible because each looked like a
cosmetic gap rather than a claim the product was failing to support.

* ``row_count`` and ``content_hash`` were ``null`` on **every** dataset of **every** published
  run. The README traces a conclusion "down to the rows"; the rows were the one link a reader
  could not check, because nothing said how many there were or which bytes they came from.
* The ``datasets`` array repeated the same dataset four to ten times per run — once per
  checkpoint save, because datasets were the only child entity written without a dedupe.
* Nothing recorded whether a dataset was real. Four of six published runs analysed a
  generated CSV, the demo index said "recorded against live data", and the word "synthetic"
  appeared nowhere a reader could see it.

The last one is the one that matters most, and it is not a UI bug. A system whose entire
argument is that it reports what it can and cannot support does not get to be vague about
its own inputs.
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
from agentic.domain.manifest import DatasetOrigin
from backend.db.base import Base
from backend.models.investigation import Investigation as InvestigationRow
from backend.schemas.investigation import build_detail
from backend.services.investigation_store import SqlAlchemyInvestigationStore

ROWS = 16


@pytest.fixture
def factory() -> Iterator[sessionmaker[Session]]:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, expire_on_commit=False)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "entity": ["A"] * ROWS,
            "period": [f"2021-{i:02d}" for i in range(ROWS)],
            "revenue": [5 + 6 * i for i in range(ROWS)],
        }
    )


def _manifest(df: pd.DataFrame, origin: DatasetOrigin = DatasetOrigin.unknown):
    return InMemoryDatasetAdapter(
        frame=df, time_field="period", entity_id_fields=["entity"],
        role_hints={"revenue": ColumnRole.metric},
    ).build_manifest(AdapterRequest(parameters={"dataset_origin": origin.value}))


@pytest.fixture
def detail(factory: sessionmaker[Session]):
    df = _frame()
    session = factory()
    investigation = InvestigationLoop().start(
        "Is revenue rising over these periods, or is volatility the explanation?",
        manifest=_manifest(df, DatasetOrigin.synthetic), frame=df, seed="prov",
        store=SqlAlchemyInvestigationStore(session),
    )
    row = session.scalar(
        select(InvestigationRow).where(InvestigationRow.domain_id == investigation.id)
    )
    assert row is not None
    yield build_detail(row)
    session.close()


def test_the_dataset_appears_exactly_once(detail) -> None:
    """
    One dataset, one entry. The run checkpoints several times and used to write a row each
    time, so a reader saw the same file listed seven times and could reasonably conclude the
    run had analysed seven of them.
    """
    assert len(detail.datasets) == 1


def test_the_row_count_is_reported(detail) -> None:
    assert detail.datasets[0].row_count == ROWS


def test_the_content_hash_is_reported(detail) -> None:
    """Without this the trace stops one link short of the bytes it claims to reach."""
    content_hash = detail.datasets[0].content_hash
    assert content_hash and content_hash.startswith("sha256:")


def test_generated_data_is_labelled_as_generated(detail) -> None:
    assert detail.datasets[0].origin == "synthetic"


def test_an_undeclared_dataset_is_unknown_not_live(factory: sessionmaker[Session]) -> None:
    """
    The default has to fail closed. Assuming real data because nobody said otherwise is
    exactly the claim this field exists to stop anyone making by accident.
    """
    df = _frame()
    session = factory()
    investigation = InvestigationLoop().start(
        "Is revenue rising over these periods, or is volatility the explanation?",
        manifest=_manifest(df), frame=df, seed="unknown-origin",
        store=SqlAlchemyInvestigationStore(session),
    )
    row = session.scalar(
        select(InvestigationRow).where(InvestigationRow.domain_id == investigation.id)
    )
    assert row is not None

    assert build_detail(row).datasets[0].origin == "unknown"
    session.close()


def test_edgar_declares_itself_live_without_being_asked() -> None:
    """
    The EDGAR adapter fetches real filings, so it is the one source that knows its own origin
    and should not depend on a caller remembering to say so.
    """
    from agentic.adapters.edgar import EDGARAdapter

    source = EDGARAdapter.build_manifest.__doc__ or ""
    assert source  # the method exists and is documented

    from backend.services.agentic_investigation_execution_service import _dataset_origin

    assert _dataset_origin({}, adapter_id="edgar") is DatasetOrigin.live
    assert _dataset_origin({}, adapter_id="in_memory") is DatasetOrigin.unknown
    assert (
        _dataset_origin({"dataset_origin": "synthetic"}, adapter_id="in_memory")
        is DatasetOrigin.synthetic
    )
    # A value nobody recognises must not be trusted into the payload.
    assert (
        _dataset_origin({"dataset_origin": "definitely-real"}, adapter_id="in_memory")
        is DatasetOrigin.unknown
    )
