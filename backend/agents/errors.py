"""Agent-stage failures (parsing / validation — not provider transport)."""


class AgentFailureCode:
    """Stable codes on :class:`AgentOutputError` for metrics and trace classification."""

    MODEL_EMPTY = "model_output_empty"
    MODEL_JSON = "model_output_invalid_json"
    MODEL_SCHEMA = "model_output_schema_invalid"
    MODEL_SEMANTIC = "model_output_semantic_invalid"


class AgentOutputError(ValueError):
    """
    Model output could not be parsed, failed schema validation, or failed semantic handoff checks.

    ``code`` is one of :class:`AgentFailureCode` constants for downstream classification.
    """

    def __init__(self, message: str, *, code: str = AgentFailureCode.MODEL_SEMANTIC) -> None:
        super().__init__(message)
        self.code = code
