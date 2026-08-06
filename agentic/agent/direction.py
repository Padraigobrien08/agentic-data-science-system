"""
Directional intent parsed from natural-language text.

Shared by the fixture policy (interpreting a goal) and the evidence updater (reading what a
hypothesis asserts), so the two can never disagree about what "up" means.

Two rules matter here, and both were learned from a real failure:

1. **Match on word boundaries, not substrings.** ``"rainfall_mm is increasing"`` contains the
   substring ``fall``, so substring matching read a rising series as a claim about decline.
   Any metric whose name embeds a direction word (rainfall, shortfall, upstream, downtime)
   hit this.
2. **Earliest match wins.** When both directions appear, the one stated first is the claim;
   fixed precedence made the answer depend on which list happened to be checked first, and
   the two call sites had opposite precedence.
"""

from __future__ import annotations

import re
from typing import Literal

Direction = Literal["up", "down"]

# Patterns are written per-word rather than as bare stems, because how far a match may run
# differs by word and getting it wrong reads a metric *name* as a directional claim:
#
#   "growth"    is a noun in metric names (revenue_growth_qoq) — not a claim, so `grow`
#               must not match it, while "growing" / "grew" must.
#   "upstream", "downtime", "download"  begin with a direction word at a word boundary, so
#               `up` and `down` are whole-word only.
#   "increas"   has no such collisions, so an open-ended stem is safe.
_UP_PATTERNS: tuple[str, ...] = (
    r"increas\w*",
    r"improv\w*",
    r"climb\w*",
    r"ris(?:e|es|ing|en)\b",
    r"grow(?:s|ing)?\b",
    r"grew\b",
    r"gain(?:s|ing|ed)?\b",
    r"up\b",
    r"higher\b",
)
_DOWN_PATTERNS: tuple[str, ...] = (
    r"decreas\w*",
    r"declin\w*",
    r"deteriorat\w*",
    r"worsen\w*",
    r"shrink\w*",
    r"shr(?:ank|unk)\b",
    r"fall(?:s|ing|en)?\b",
    r"fell\b",
    r"drop(?:s|ping|ped)?\b",
    r"down\b",
    r"lower\b",
)


def _pattern(patterns: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(patterns) + r")", re.IGNORECASE)


_UP_RE = _pattern(_UP_PATTERNS)
_DOWN_RE = _pattern(_DOWN_PATTERNS)


def parse_direction(text: str) -> Direction | None:
    """The direction ``text`` asserts, or ``None`` when it is non-directional.

    >>> parse_direction("rainfall_mm is increasing over time")
    'up'
    >>> parse_direction("revenue is falling")
    'down'
    >>> parse_direction("compare revenue between groups") is None
    True
    """
    if not text:
        return None
    up = _UP_RE.search(text)
    down = _DOWN_RE.search(text)
    if up and down:
        # Both stated: the earlier one is the claim, the later is usually context.
        return "up" if up.start() < down.start() else "down"
    if up:
        return "up"
    if down:
        return "down"
    return None


def direction_sign(text: str) -> int | None:
    """``+1`` for up, ``-1`` for down, ``None`` when non-directional."""
    direction = parse_direction(text)
    if direction is None:
        return None
    return 1 if direction == "up" else -1
