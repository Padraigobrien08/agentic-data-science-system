"""Agent-stage failures (parsing / validation — not provider transport)."""


class AgentOutputError(ValueError):
    """Model output could not be parsed or failed schema validation."""
