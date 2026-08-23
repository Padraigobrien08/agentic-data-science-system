"""
Verifying a written answer against the state it claims to describe.

The loop may ask a model to *write* its conclusion, because a wall of joined hypothesis
statements is not an answer anyone reads. It may not let the model *state figures*: the
governing rule is that no number in a trace originates from a language model, and prose is
exactly where an invented number is hardest to spot and most likely to be believed.

So the model writes, and this module checks. Every numeric token in the prose must match a
value the run actually recorded; one that does not invalidates the whole narrative, not just
the sentence containing it. That is deliberate — a paragraph with one fabricated figure is
not partially trustworthy, and there is no safe way to excise the bad clause and keep the
rest. The caller falls back to the deterministic statement, which is less readable and
entirely true.

This module is pure: no I/O, no model, no domain imports beyond plain values.
"""

from __future__ import annotations

import re

__all__ = ["AllowedNumbers", "extract_numbers", "verify_narrative"]

# Digits with optional thousands separators, decimals and a percent sign.
_NUMERIC = re.compile(r"\d[\d,]*(?:\.\d+)?%?")

# Small number words carry the same risk as digits — "both claims held" is a claim about a
# count. Bounded at twenty on purpose: beyond that, prose says the digits.
_WORD_NUMBERS: dict[str, float] = {
    "zero": 0, "no": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "both": 2, "neither": 2, "half": 0.5,
}

_WORD_RE = re.compile(r"\b(" + "|".join(_WORD_NUMBERS) + r")\b", re.IGNORECASE)

_TOLERANCE = 1e-6


class AllowedNumbers:
    """
    Every value the prose is permitted to state, gathered from recorded state.

    A confidence is admitted in both forms a writer might use — ``0.95`` and ``95`` — because
    which one appears is a style choice, not a factual one. Nothing else is widened: a count
    is admitted as itself.
    """

    def __init__(self) -> None:
        self._values: set[float] = set()

    def add_count(self, value: int | float | None) -> AllowedNumbers:
        if value is not None:
            self._values.add(float(value))
        return self

    def add_confidence(self, value: float | None) -> AllowedNumbers:
        if value is None:
            return self
        self._values.add(float(value))
        # The same reading as a percentage, and rounded, since prose says "95%" not "95.0%".
        self._values.add(round(float(value) * 100, 4))
        self._values.add(float(round(value * 100)))
        return self

    def add_many_counts(self, values: object) -> AllowedNumbers:
        if isinstance(values, dict):
            values = values.values()
        if isinstance(values, (list, tuple, set, frozenset)) or hasattr(values, "__iter__"):
            for v in values:  # type: ignore[union-attr]
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    self.add_count(v)
        return self

    def __contains__(self, value: float) -> bool:
        return any(abs(value - allowed) <= _TOLERANCE for allowed in self._values)

    def __len__(self) -> int:
        return len(self._values)


def _parse(token: str) -> list[float]:
    """
    Readings of one token. ``95%`` may mean 95 or 0.95 depending on how the state stores it,
    and admitting both is safe: each reading is still checked against recorded values.
    """
    percent = token.endswith("%")
    raw = token.rstrip("%").replace(",", "")
    try:
        value = float(raw)
    except ValueError:
        return []
    return [value, value / 100] if percent else [value]


def extract_numbers(text: str) -> list[str]:
    """Numeric tokens in ``text``, digits and small number words alike, in order."""
    return [m.group(0) for m in _NUMERIC.finditer(text)] + [
        m.group(0).lower() for m in _WORD_RE.finditer(text)
    ]


def verify_narrative(text: str, allowed: AllowedNumbers) -> str | None:
    """
    ``text`` when every figure in it is one the run recorded, else ``None``.

    Returning ``None`` rather than a repaired string is the point: the caller has a true
    statement to fall back to, and a narrative that has been edited to remove a lie is not
    the narrative the model produced.
    """
    cleaned = text.strip()
    if not cleaned:
        return None

    for token in _NUMERIC.finditer(cleaned):
        readings = _parse(token.group(0))
        if not readings or not any(r in allowed for r in readings):
            return None

    for token in _WORD_RE.finditer(cleaned):
        if _WORD_NUMBERS[token.group(0).lower()] not in allowed:
            return None

    return cleaned
