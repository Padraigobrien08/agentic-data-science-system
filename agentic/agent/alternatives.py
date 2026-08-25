"""
Recognising a goal that poses two rival explanations.

"Is service quality degrading, **or** is rising order volume the explanation?" asks which of
two accounts is right. It is not asking whether both are true, and an answer of "both, at 0.95
each" is not a generous reading of the question — it is a failure to have answered it.

The loop used to depend entirely on a model noticing the conflict later, at critique time,
after both claims had already been scored and supported independently. That check is real but
best-effort by construction, and it missed: a published run answered an either/or question by
affirming both branches at 0.95, reported ``contradiction_found: false``, and was rendered in
the product as the most confident result in the set.

The *shape of the question* does not need a model. A goal that joins two propositions with
"or" is asking for one of them, and that is decidable here, deterministically, before a single
claim is proposed. What the model still supplies is the claims themselves; what this supplies
is the knowledge that they are rivals.

This module is pure: no I/O, no model, no domain imports.
"""

from __future__ import annotations

import re

__all__ = ["poses_alternatives"]

#: Words that begin a *proposition* rather than continuing a list of nouns.
#:
#: The discriminator that matters. "Compare revenue or margin by region" joins two nouns and
#: asks one question; "does staffing explain it, or is volume the driver" joins two clauses and
#: asks which. Requiring an auxiliary, copula or pronoun after "or" separates them without
#: parsing English, and matches every either/or goal in the recording stack.
_CLAUSE_OPENERS = (
    "is", "are", "was", "were", "does", "do", "did", "has", "have", "had",
    "can", "could", "will", "would", "should", "it", "that", "they", "this",
)

_OR_CLAUSE = re.compile(
    r",?\s+or\s+(?:if\s+)?(" + "|".join(_CLAUSE_OPENERS) + r")\b",
    re.IGNORECASE,
)

#: Enough text on the left for the disjunction to be joining two real propositions rather
#: than trailing off a fragment.
_MIN_LEAD = 12


def poses_alternatives(goal_text: str) -> bool:
    """
    True when ``goal_text`` asks which of two explanations holds, rather than asking about two
    things independently.

    Deliberately conservative: a false positive marks two unrelated claims as rivals and would
    suppress a legitimate "both are true" answer, which is a worse error than falling back to
    the model-driven critique that already exists.
    """
    text = (goal_text or "").strip()
    if not text:
        return False
    match = _OR_CLAUSE.search(text)
    if match is None:
        return False
    return len(text[: match.start()].strip()) >= _MIN_LEAD
