"""Service-layer errors (business rules)."""


class InvalidStatusTransition(ValueError):
    """Raised when a status change is not allowed for the entity."""

    def __init__(self, entity: str, current: object, target: object) -> None:
        self.entity = entity
        self.current = current
        self.target = target
        super().__init__(f"{entity}: cannot transition from {current!r} to {target!r}")
