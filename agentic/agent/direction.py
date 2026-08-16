"""
Directional intent parsed from natural-language text.

Shared by the fixture policy (interpreting a goal) and the evidence updater (reading what a
hypothesis asserts), so the two can never disagree about what "up" means.

Two questions are parsed here, and they are not the same one. :func:`parse_direction` reads
*movement* — which way a series went. :func:`parse_extreme` reads *which end of a ranking* a
goal is asking for. Both answer in the same ``up``/``down`` vocabulary because both end up in
the same field, but the word lists are separate: "weakest" names a position, not a decline.

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


# Superlatives, which are a different question from movement: "is revenue falling" asks which
# way a series moved, "which region is weakest" asks which end of a ranking to report. They are
# kept in their own lists because the evidence updater reads a *hypothesis* with the movement
# patterns above, and "the weakest region" is not a claim that anything went down.
_BEST_PATTERNS: tuple[str, ...] = (
    r"best\b",
    r"strongest\b",
    r"highest\b",
    r"largest\b",
    r"biggest\b",
    r"greatest\b",
    r"top\b",
    r"leading\b",
    r"maximum\b",
)
_WORST_PATTERNS: tuple[str, ...] = (
    r"worst\b",
    r"weakest\b",
    r"lowest\b",
    r"smallest\b",
    r"poorest\b",
    r"bottom\b",
    r"laggard\w*",
    r"minimum\b",
)


def _pattern(patterns: tuple[str, ...]) -> re.Pattern[str]:
    return re.compile(r"\b(?:" + "|".join(patterns) + r")", re.IGNORECASE)


_UP_RE = _pattern(_UP_PATTERNS)
_DOWN_RE = _pattern(_DOWN_PATTERNS)
_BEST_RE = _pattern(_BEST_PATTERNS)
_WORST_RE = _pattern(_WORST_PATTERNS)


def _earliest(text: str, up: re.Pattern[str], down: re.Pattern[str]) -> Direction | None:
    up_match = up.search(text)
    down_match = down.search(text)
    if up_match and down_match:
        # Both stated: the earlier one is the claim, the later is usually context.
        return "up" if up_match.start() < down_match.start() else "down"
    if up_match:
        return "up"
    if down_match:
        return "down"
    return None


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
    return _earliest(text, _UP_RE, _DOWN_RE)


def parse_extreme(text: str) -> Direction | None:
    """Which end of a ranking ``text`` asks about, or ``None`` when it names neither.

    ``"up"`` is the strongest/highest entity, ``"down"`` the weakest/lowest — the same
    vocabulary :attr:`~agentic.agent.policy.GoalInterpretation.direction` already uses, so a
    ranking goal can travel to the planner through the field that exists rather than a second
    one. Movement words are deliberately *not* consulted: "which region grew least" is a
    question about the bottom of a ranking, and reading its "grew" as ``up`` would answer it
    with the region that grew most.

    >>> parse_extreme("which region has the weakest on-time delivery rate?")
    'down'
    >>> parse_extreme("which product sells best?")
    'up'
    >>> parse_extreme("rank regions by revenue") is None
    True
    """
    if not text:
        return None
    return _earliest(text, _BEST_RE, _WORST_RE)


def direction_sign(text: str) -> int | None:
    """``+1`` for up, ``-1`` for down, ``None`` when non-directional."""
    direction = parse_direction(text)
    if direction is None:
        return None
    return 1 if direction == "up" else -1
