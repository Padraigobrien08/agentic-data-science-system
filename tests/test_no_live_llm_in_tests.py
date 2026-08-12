"""
The suite must not be able to call a live model provider.

`.env` on a developer machine holds a real key, so without a guard the default posture of
`pytest` is "bill the operator". These assert the guard in `tests/conftest.py` is doing its
job — that the implicit path, the one a forgotten monkeypatch falls back to, cannot reach a
provider.

They deliberately test the *environment the suite runs in*, not a function. That is the level
the mistake happened at: every individual test looked correct.
"""

from __future__ import annotations

import os

import pytest

from backend.agents.agentic_model_policy import build_agent_policy
from backend.config.settings import Settings, get_settings
from backend.llm.exceptions import LLMProviderConfigurationError
from backend.llm.factory import get_chat_completion_provider
from tests.conftest import LIVE_LLM_OPT_IN

pytestmark = pytest.mark.skipif(
    os.environ.get(LIVE_LLM_OPT_IN) == "1",
    reason="live provider explicitly opted in",
)


def test_the_environment_disables_the_provider() -> None:
    assert os.environ["EDGAR_BACKEND_LLM_PROVIDER"] == "off"
    assert os.environ["EDGAR_BACKEND_OPENAI_API_KEY"] == ""
    assert os.environ["OPENAI_API_KEY"] == ""


def test_ambient_settings_report_no_provider() -> None:
    """What any code calling get_settings() during a test actually sees."""
    settings = get_settings()
    assert settings.llm_provider == "off"
    key = settings.openai_api_key
    assert key is None or key.get_secret_value() == ""


def test_the_factory_refuses_to_build_from_ambient_settings() -> None:
    with pytest.raises(LLMProviderConfigurationError):
        get_chat_completion_provider(get_settings())


def test_build_agent_policy_degrades_to_the_fixture_policy() -> None:
    """
    The exact path that billed real money.

    A test forgot to patch build_agent_policy on the module that reads it; the call fell
    through to the configured provider and hit OpenAI. With the guard, that fall-through
    lands on the deterministic policy instead of the network.
    """
    from agentic.agent.fixture_policy import FixtureAgentPolicy

    assert isinstance(build_agent_policy(get_settings()), FixtureAgentPolicy)


def test_turning_the_provider_back_on_still_finds_no_credential() -> None:
    """Disabling alone is not enough — the key is blanked so re-enabling cannot reach out."""
    with pytest.raises(LLMProviderConfigurationError):
        get_chat_completion_provider(Settings(llm_provider="openai"))


def test_an_explicit_provider_is_still_constructible() -> None:
    """
    The guard bounds the *ambient* posture, not the suite's ability to test provider wiring.
    Init arguments outrank the environment, so a test that means to build one still can.
    """
    from pydantic import SecretStr

    provider = get_chat_completion_provider(
        Settings(llm_provider="openai", openai_api_key=SecretStr("sk-test-key"))
    )
    assert provider.provider_id == "openai"
