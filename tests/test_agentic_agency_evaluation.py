"""
Agency evaluation cases — proven end-to-end through the production create path.

These drive `InvestigationCreateService` (the user-facing entry point) over a
**non-EDGAR** dataset with arbitrary column names, then assert the agency
properties on the *persisted* investigation: input-agnosticism, adaptivity
(different goals take different experiment paths), falsification / hypothesis
movement under contradictory evidence, and typed termination. Offline and
deterministic (fixture policy) — complements the loop-level tests in
`tests/agentic/test_investigation_loop.py` by exercising the wired backend path.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import backend.models  # noqa: F401
from agentic.agent.fixture_policy import FixtureAgentPolicy
from agentic.domain import Investigation as DomainInvestigation
from agentic.domain.enums import ConclusionDisposition, HypothesisStatus, TerminationReason
from backend.config.settings import Settings
from backend.db.base import Base
from backend.models.project import Project
from backend.models.user import User
from backend.repositories.investigation_repository import SqlAlchemyInvestigationRepository
from backend.services import agentic_investigation_execution_service as exec_mod
from backend.services.investigation_create_service import InvestigationCreateService

_TYPED_TERMINATION_REASONS = {r.value for r in TerminationReason}


@pytest.fixture
def session(monkeypatch) -> Iterator[Session]:
    monkeypatch.setattr(exec_mod, "build_agent_policy", lambda s: FixtureAgentPolicy())
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine, expire_on_commit=False)()
    try:
        yield s
    finally:
        s.close()


def _project(session: Session) -> tuple[uuid.UUID, uuid.UUID]:
    user = User(email=f"{uuid.uuid4().hex[:8]}@example.com")
    session.add(user)
    session.flush()
    project = Project(owner_user_id=user.id, name="p")
    session.add(project)
    session.commit()
    return project.id, user.id


def _run(session: Session, project_id, user_id, *, goal: str, csv: str,
         time_field: str | None, entity_fields: list[str]) -> DomainInvestigation:
    result = InvestigationCreateService(session, settings=Settings(agentic_engine_enabled=True)).create_and_run(
        project_id=project_id, user_id=user_id, goal=goal,
        dataset_format="csv", csv_text=csv, records=None, name="ds",
        time_field=time_field, entity_id_fields=entity_fields,
    )
    return SqlAlchemyInvestigationRepository(session).load_domain(result.investigation_id)


def _executed(inv: DomainInvestigation) -> list[str]:
    return [r.tool_name for r in inv.state.completed_experiments + inv.state.failed_experiments]


# Non-EDGAR domain, arbitrary column names (proves no domain assumptions leak in).
def _trend_csv(store: str = "north", n: int = 8, start: float = 10.0, step: float = 6.0) -> str:
    rows = [f"{store},2023-{i:02d},{start + step * i}" for i in range(n)]
    return "store,week,sales\n" + "\n".join(rows)


def test_input_agnostic_run_over_non_edgar_csv(session: Session) -> None:
    project_id, user_id = _project(session)
    inv = _run(session, project_id, user_id, goal="are sales trending up over time?",
               csv=_trend_csv(), time_field="week", entity_fields=["store"])
    assert inv.is_terminal()
    assert inv.state.termination is not None
    assert inv.state.termination.reason.value in _TYPED_TERMINATION_REASONS
    assert len(_executed(inv)) >= 1  # deterministic experiments ran over the frame
    # goal uses adapter_id "in_memory" — no EDGAR tools involved
    assert not any(t.startswith("edgar_") for t in _executed(inv))


def test_adaptivity_different_goals_take_different_paths(session: Session) -> None:
    project_id, user_id = _project(session)
    csv = _trend_csv()
    trend = _run(session, project_id, user_id, goal="show the trend of sales over time",
                 csv=csv, time_field="week", entity_fields=["store"])
    rank = _run(session, project_id, user_id, goal="rank stores by sales",
                csv=csv, time_field="week", entity_fields=["store"])
    assert set(_executed(trend)) != set(_executed(rank))


def test_contradictory_evidence_moves_hypothesis(session: Session) -> None:
    project_id, user_id = _project(session)
    up = _trend_csv("north", n=6, start=10, step=5).splitlines()
    down = [f"south,2023-{i:02d},{40 - 6 * i}" for i in range(6)]
    csv = "\n".join(up + down)  # north rises, south falls
    inv = _run(session, project_id, user_id, goal="sales are increasing over time",
               csv=csv, time_field="week", entity_fields=["store"])
    statuses = {h.status for h in inv.state.hypotheses}
    # the agent did not blindly confirm: the hypothesis moved off "supported"
    assert statuses & {HypothesisStatus.weakened, HypothesisStatus.rejected, HypothesisStatus.unresolved}


def test_flat_data_is_insufficient_evidence(session: Session) -> None:
    project_id, user_id = _project(session)
    csv = "store,week,sales\n" + "\n".join(f"north,2023-{i:02d},5.0" for i in range(6))
    inv = _run(session, project_id, user_id, goal="are sales increasing over time?",
               csv=csv, time_field="week", entity_fields=["store"])
    assert inv.state.current_conclusion is not None
    assert inv.state.current_conclusion.disposition is ConclusionDisposition.insufficient_evidence
