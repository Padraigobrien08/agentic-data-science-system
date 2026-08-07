"""
Injectable monotonic clock for the investigation loop.

The loop needs elapsed wall time for two reasons: enforcing the elapsed-time
budget/safety limits, and timing component decisions for observability. Both must
stay deterministic under test, so the clock is injected rather than read from
:mod:`time` at the call site.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Clock(Protocol):
    """Monotonic time source. Only differences between readings are meaningful."""

    def monotonic(self) -> float: ...


class MonotonicClock:
    """Default clock backed by :func:`time.perf_counter`."""

    def monotonic(self) -> float:
        return time.perf_counter()


@dataclass
class ManualClock:
    """Test clock advanced explicitly, so elapsed-time behavior is deterministic."""

    now: float = 0.0

    def monotonic(self) -> float:
        return self.now

    def advance(self, seconds: float) -> float:
        self.now += seconds
        return self.now
