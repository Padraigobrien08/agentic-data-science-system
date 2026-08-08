"""
The dashboard seeding workload — its catalogue, and its offline guarantee.

Only the pure parts are tested here; driving a live stack belongs in the phase's manual
verification, not in the suite. What matters is the two properties that would make the workload
useless or unsafe if they broke.

**Variety.** `docs/observability.md` names the signatures the agent-loop dashboard exposes: a
flat single-tool profile means the loop is not adapting, and only `-> supported` transitions
mean it is never challenged. A catalogue that quietly collapsed to one kind of question would
reproduce exactly those signatures and make working instrumentation look broken — so the spread
is asserted rather than assumed.

**No spend.** The standing goal forbids spending money. The workload is free because the backend
falls back to the deterministic fixture policy with no provider configured; that fallback is
asserted here so a change to it cannot silently make this script expensive.
"""

from __future__ import annotations

import importlib.util
import io
import sys
from pathlib import Path

import pandas as pd
import pytest

import backend.agents.agentic_model_policy as policy_mod
from agentic.evaluation.fixtures import FIXTURES
from backend.config.settings import Settings
from backend.llm.exceptions import LLMProviderConfigurationError

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "seed-agent-activity.py"


def _load_seeder():
    """
    Import the script by path — it is a script, not an installed module.

    Registered in ``sys.modules`` before execution because ``@dataclass`` resolves its own
    module during class creation and fails on an unregistered one.
    """
    spec = importlib.util.spec_from_file_location("seed_agent_activity", _SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


seeder = _load_seeder()


# -- variety -----------------------------------------------------------------


def test_the_catalogue_is_not_a_single_repeated_question() -> None:
    assert len(seeder.GOAL_CATALOGUE) >= 10
    assert len({g.goal for g in seeder.GOAL_CATALOGUE}) >= 10


def test_the_catalogue_spans_several_intents() -> None:
    """
    Uses the same keyword table the deterministic policy uses, so this measures the spread the
    loop will actually see rather than a spread we assert exists.
    """
    from agentic.agent.fixture_policy import _INTENT_KEYWORDS

    intents = set()
    for goal in seeder.GOAL_CATALOGUE:
        text = f" {goal.goal.lower()} "
        matched = next(
            (i.value for i, kws in _INTENT_KEYWORDS if any(k in text for k in kws)), "general"
        )
        intents.add(matched)

    assert len(intents) >= 5, f"catalogue only reaches {sorted(intents)}; the tool mix will be flat"


def test_the_catalogue_includes_questions_the_data_cannot_support() -> None:
    """Without these the termination breakdown is one slice and the error panels stay empty."""
    non_converging = {"flat", "too_short", "noisy_no_trend", "response_latency_flat",
                      "api_latency_rising"}

    used = {g.fixture_id for g in seeder.GOAL_CATALOGUE}

    assert used & non_converging, "every seeded goal converges; terminations will not vary"


# -- datasets ----------------------------------------------------------------


@pytest.mark.parametrize("goal", seeder.GOAL_CATALOGUE, ids=lambda g: f"{g.fixture_id}:{g.goal[:24]}")
def test_every_goal_renders_valid_csv(goal) -> None:
    text = goal.csv()
    frame = pd.read_csv(io.StringIO(text))

    assert not frame.empty
    assert list(frame.columns), "rendered CSV has no columns"


@pytest.mark.parametrize("goal", seeder.GOAL_CATALOGUE, ids=lambda g: g.fixture_id)
def test_structural_hints_name_real_columns(goal) -> None:
    """
    A time_field or entity field that is not in the frame would make the adapter mis-read the
    dataset, and the resulting runs would exercise the wrong tools — variety that is not real.
    """
    columns = set(pd.read_csv(io.StringIO(goal.csv())).columns)

    if goal.time_field is not None:
        assert goal.time_field in columns, f"{goal.fixture_id}: no column {goal.time_field!r}"
    for entity_field in goal.entity_id_fields:
        assert entity_field in columns, f"{goal.fixture_id}: no column {entity_field!r}"


def test_every_referenced_fixture_is_registered() -> None:
    missing = sorted({g.fixture_id for g in seeder.GOAL_CATALOGUE} - set(FIXTURES))

    assert not missing, f"catalogue references unregistered fixtures: {missing}"


# -- the offline guarantee ---------------------------------------------------


def test_the_backend_falls_back_to_the_free_deterministic_policy(monkeypatch) -> None:
    """
    Why the workload costs nothing. If this fallback ever went away, seeding on a machine
    without a provider would fail rather than run free — and seeding on one *with* a provider
    would quietly bill for every run.
    """

    def _unconfigured(settings):  # noqa: ANN001 - test double
        raise LLMProviderConfigurationError("no provider")

    monkeypatch.setattr(policy_mod, "get_chat_completion_provider", _unconfigured)

    policy = policy_mod.build_agent_policy(Settings())

    assert type(policy).__name__ == "FixtureAgentPolicy"


def test_the_seeder_reaches_no_external_service() -> None:
    """
    Datasets are rendered locally from fixtures; the only host the script talks to is the API
    base URL it was given.
    """
    source = _SCRIPT.read_text(encoding="utf-8")

    for forbidden in ("sec.gov", "openai.com", "api.anthropic.com"):
        assert forbidden not in source, f"seeder references external host {forbidden!r}"
    assert "127.0.0.1" in source, "the default base URL should be local"


def test_the_docstring_states_the_free_offline_guarantee_and_its_caveat() -> None:
    doc = seeder.__doc__ or ""

    assert "offline" in doc.lower()
    assert "cost money" in doc.lower() or "costs nothing" in doc.lower()
