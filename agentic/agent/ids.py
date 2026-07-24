"""
Deterministic id generation for the investigation loop.

Ids are a pure function of (seed, kind, index-derived-from-state), so a loop
resumed from a checkpoint mints the same subsequent ids as an uninterrupted run.
"""

from __future__ import annotations


class DeterministicIds:
    """Stable, resume-safe id factory seeded per investigation."""

    def __init__(self, seed: str) -> None:
        self.seed = seed

    def make(self, kind: str, index: int) -> str:
        return f"{self.seed}-{kind}-{index}"
