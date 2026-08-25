"""
Verifying a written answer against the state it claims to describe.

The loop may ask a model to *write* its conclusion, because a wall of joined hypothesis
statements is not an answer anyone reads. It may not let the model *state figures*: the
governing rule is that no number in a trace originates from a language model, and prose is
exactly where an invented number is hardest to spot and most likely to be believed.

So the model writes, and this module checks. One figure that does not check out invalidates
the whole narrative, not just the sentence containing it. That is deliberate — a paragraph
with one fabricated figure is not partially trustworthy, and there is no safe way to excise
the bad clause and keep the rest. The caller falls back to the deterministic statement, which
is less readable and entirely true.

## Why a figure must be *labelled*, not merely *recorded*

The first version of this check held one flat set of every number the run recorded and asked
only "does this token appear in it?". That is much weaker than it sounds. A run with seven
experiments and three open questions admits 7 and 3, so ``"Revenue grew 7% while margin fell
3%."`` passed — two fabricated financial figures, each borrowing the authority of an unrelated
count. The set was untyped and unpositioned, so any recorded number could be spent as any
other quantity anywhere in the prose.

A figure is therefore checked against the role the prose *puts it in*. ``7`` is admissible as
a count of experiments only in a clause that is talking about experiments; the same token next
to a percent sign and the word "revenue" matches no role and is refused. This costs some
honest phrasings, and that is the right side to err on: rejection returns a true answer that
reads worse, acceptance returns a false one that reads well.

## Digits are held to a stricter standard than number words

Role-labelling is applied to digits only. Number words are checked against the run's recorded
values but not against the role the prose puts them in, and the asymmetry is deliberate rather
than a gap someone forgot to close.

A fabricated *statistic* is written in digits — that is what "0.87" or "7%" is for. Small
number words are overwhelmingly idiomatic: real recorded output says "signs pointing in both
directions", "neither was strong enough to stand", "the two explanations", "one over the
other". None of those is a measurement, and none sits next to a word naming a findings role.
Role-labelling them rejected four of the seven narratives this loop has actually produced,
which is the same over-rejection that made an earlier version of this check unusable. The
residual risk is a miscounted claim — visible immediately against the deterministic statement
printed beside it — not an invented figure.

## What this does not check

Relations without numerals — "the stronger finding", "more refuting than supporting evidence"
— are left alone. They describe orderings the run genuinely holds, and rejecting them would
take most honest prose with them. But a *multiplicative* relation ("more than twice as fast",
"roughly doubled", "an order of magnitude larger") asserts a ratio the run never computed, and
is refused for the same reason a bare number is: it is a quantity the model made up.

This module is pure: no I/O, no model, no domain imports beyond plain values.
"""

from __future__ import annotations

import re

__all__ = ["AllowedFigures", "extract_numbers", "verify_narrative"]

# Digits with optional sign, thousands separators, decimals and a percent sign.
#
# The sign is part of the value. Without it the pattern was direction-blind: a run recording a
# 5-point rise admitted "fell by -5 percentage points", because only the magnitude was ever
# compared and the minus was discarded before parsing.
_NUMERIC = re.compile(r"(?<![\w.])[-−+]?\d[\d,]*(?:\.\d+)?%?")

# Small number words carry the same risk as digits — "both claims held" is a claim about a
# count. Bounded at twenty on purpose: beyond that, prose says the digits.
#
# `no`, `one` and `half` are deliberately absent, and that is a concession learned from real
# output. As numerals they are indistinguishable from their far more common function-word
# senses — "no decisive confirmation", "the stronger one", "one of the two" — so checking
# them rejected honest prose at a rate that made the whole feature unusable: five of eight
# recorded narratives were discarded, most of them over the word "no". Digits stay strict,
# which is where a fabricated statistic actually lives; unambiguous count words stay checked.
_WORD_NUMBERS: dict[str, float] = {
    "zero": 0, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11,
    "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
    "both": 2, "neither": 2,
}

_WORD_RE = re.compile(r"\b(" + "|".join(_WORD_NUMBERS) + r")\b", re.IGNORECASE)

#: Roles a figure can fill, and the words that put it in one. Matched case-insensitively as
#: substrings, so "hypothes" covers hypothesis/hypotheses and "experiment" covers the plural.
#: Kept as disjoint as the vocabulary allows: where two roles could claim the same word the
#: figure becomes admissible under either, which is a hole, so the words are chosen to avoid
#: it rather than the ambiguity being resolved after the fact.
_ROLE_LABELS: dict[str, tuple[str, ...]] = {
    "hypotheses": ("hypothes", "claim", "explanation"),
    "evidence": ("evidence", "item"),
    "experiments": ("experiment", "tool", "analysis", "analyses", "step"),
    "supported": ("supported", "stood", "held up"),
    "open_questions": ("question",),
    # "percent" spelled out labels a rate as surely as the "%" sign does.
    "confidence": ("confidence", "confident", "certainty", "percent"),
    "rows": ("row", "data point", "datapoint", "observation"),
    "supporting_evidence": ("supporting", "in favour", "in favor", "for it"),
    "refuting_evidence": ("refuting", "against", "contradict"),
}

#: An explicit confidence word, as opposed to the ``%`` sign that merely implies one. Only
#: this overrides the metric veto in :func:`_digit_checks_out`.
_CONFIDENCE_WORD = re.compile(r"confiden|certainty", re.IGNORECASE)

#: How far either side of a figure to look for the word that gives it a role. Wide enough for
#: "confidence of 0.95" and "0.95 confidence", narrow enough that a role word in the next
#: clause does not launder an unrelated number.
_WINDOW = 34

#: The tighter window in which a role word *names* the figure rather than merely sitting near
#: it: "2 refuting evidence items" — the noun is the next word, and there is nothing ambiguous
#: about what the 2 counts.
#:
#: This distinction is what stops the metric veto from firing on honest prose. Real recorded
#: output reads "...and 2 refuting evidence items. The revenue-growth claim was supported",
#: where `revenue` lands 33 characters after the `2` — inside `_WINDOW`, in the *next
#: sentence*, describing something else entirely. Vetoing on that discarded four of six
#: narratives, each of which had labelled every figure exactly as asked.
_TIGHT_WINDOW = 22

#: Quantitative relations stated without a numeral. Each asserts a ratio the run never
#: computed, so each is a fabricated figure wearing words. Scoped tightly on purpose:
#: "half of" is a ratio, "the first half of the period" is a time span, and only the former
#: should cost the narrative. Ordinal and qualitative comparisons are deliberately absent —
#: see the module docstring.
_RATIO_CLAIMS = re.compile(
    r"\b(?:"
    r"twice|thrice|"
    r"doubl(?:e|es|ed|ing)|tripl(?:e|es|ed|ing)|quadrupl(?:e|es|ed|ing)|"
    r"halve[sd]?|halving|half\s+(?:of|the|as)\b|"
    r"(?:a|one)[-\s](?:third|quarter|fifth)\s+(?:of|reduction|increase)|"
    r"orders?\s+of\s+magnitude|"
    r"(?:by\s+)?a\s+factor\s+of|"
    r"\b[\d.]+[-\s]?fold|"
    r"\d+\s+times\s+(?:as|more|less|higher|lower|larger|smaller|greater|faster|slower)"
    r")",
    re.IGNORECASE,
)

_TOLERANCE = 1e-6


class AllowedFigures:
    """
    Every value the prose may state, and the role it may state it as.

    A confidence is admitted in both forms a writer might use — ``0.95`` and ``95`` — because
    which one appears is a style choice, not a factual one. Nothing else is widened: a count
    is admitted as itself, under its own role and no other.
    """

    def __init__(self) -> None:
        self._by_role: dict[str, set[float]] = {}
        self._metric_terms: set[str] = set()

    def add(self, role: str, value: int | float | None) -> AllowedFigures:
        if value is None or isinstance(value, bool):
            return self
        self._by_role.setdefault(role, set()).add(float(value))
        return self

    def add_confidence(self, value: float | None, *, role: str = "confidence") -> AllowedFigures:
        if value is None:
            return self
        self.add(role, float(value))
        # The same reading as a percentage, and rounded, since prose says "95%" not "95.0%".
        self.add(role, round(float(value) * 100, 4))
        self.add(role, float(round(value * 100)))
        return self

    def add_counts(self, values: object) -> AllowedFigures:
        """Admit a mapping of role name to count, e.g. the synthesizer's ``counts`` block."""
        if isinstance(values, dict):
            for role, v in values.items():
                if isinstance(v, (int, float)) and not isinstance(v, bool):
                    self.add(str(role), v)
        return self

    def add_metric_terms(self, names: object) -> AllowedFigures:
        """
        Name the dataset's own columns, so a figure attached to one can be refused.

        The findings handed to the writer contain claim statuses, confidences and counts —
        and **no measurements at all**. So a digit in a clause about ``net_margin`` or
        ``on_time_rate`` is fabricated by construction, whatever its value happens to collide
        with. This is what stops a recorded confidence of ``0.05`` from licensing "net margin
        deteriorated by 5%": the number is real, the thing it is attached to is not.
        """
        if isinstance(names, (list, tuple, set, frozenset)):
            for name in names:
                for word in re.split(r"[^a-z0-9]+", str(name).lower()):
                    # One- and two-letter fragments ("of", "qo") match far too much prose.
                    if len(word) > 2:
                        self._metric_terms.add(word)
        return self

    def mentions_a_metric(self, window: str) -> bool:
        return any(term in window for term in self._metric_terms)

    def roles_for(self, value: float) -> set[str]:
        """Every role under which ``value`` is a figure the run recorded."""
        return {
            role
            for role, allowed in self._by_role.items()
            if any(abs(value - a) <= _TOLERANCE for a in allowed)
        }

    def any_role_has(self, value: float) -> bool:
        """``value`` is recorded somewhere, without regard to role. Number words only."""
        return bool(self.roles_for(value))

    def __len__(self) -> int:
        return sum(len(v) for v in self._by_role.values())


def _parse(token: str) -> list[float]:
    """
    Readings of one token. ``95%`` may mean 95 or 0.95 depending on how the state stores it,
    and admitting both is safe: each reading is still checked against a recorded value *in a
    matching role*.
    """
    raw = token.replace("−", "-").replace(",", "")
    percent = raw.endswith("%")
    raw = raw.rstrip("%")
    try:
        value = float(raw)
    except ValueError:
        return []
    return [value, value / 100] if percent else [value]


def _roles_in_context(
    text: str, start: int, end: int, *, token: str = "", window: int = _WINDOW,
    implied: bool = True,
) -> set[str]:
    """
    The roles named close enough to ``text[start:end]`` to be describing it.

    A trailing percent sign counts as naming ``confidence`` on its own. Every other figure the
    findings carry is a count, so a rate has exactly one thing it can be here, and "both claims
    held at 95%" is ordinary phrasing that no nearby word labels. The value is still checked
    against the recorded confidences — this admits the *role*, never the number.
    """
    near = _window_around(text, start, end, window)
    roles = {
        role
        for role, labels in _ROLE_LABELS.items()
        if any(label in near for label in labels)
    }
    # An *implied* role, which is why it can be switched off. It is enough to say what an
    # otherwise-unlabelled figure must be, but not enough to prove a figure is labelled —
    # "net margin deteriorated by 5%" would otherwise claim to name its own role and skip
    # the metric veto entirely.
    if implied and token.endswith("%"):
        roles.add("confidence")
    return roles


def extract_numbers(text: str) -> list[str]:
    """Numeric tokens in ``text``, digits and small number words alike, in order."""
    return [m.group(0) for m in _NUMERIC.finditer(text)] + [
        m.group(0).lower() for m in _WORD_RE.finditer(text)
    ]


def _window_around(text: str, start: int, end: int, window: int = _WINDOW) -> str:
    return text[max(0, start - window):min(len(text), end + window)].lower()


def _digit_checks_out(text: str, match: re.Match[str], allowed: AllowedFigures) -> bool:
    """A digit is kept only when some reading of it is recorded *under a role the prose puts
    it in*, and the clause is not describing a dataset metric. An unlabelled figure fails
    here even when the value happens to be recorded somewhere."""
    readings = _parse(match.group(0))
    if not readings:
        return False

    # A figure whose role noun is the very next thing said is not ambiguous — "2 refuting
    # evidence items" counts evidence, whatever else the sentence goes on to mention. Checked
    # first, and on its own terms: the metric veto exists to catch figures with *no* clear
    # role, and applying it here rejects the exact phrasing the writer was asked for.
    named = _roles_in_context(
        text, match.start(), match.end(), token=match.group(0), window=_TIGHT_WINDOW,
        implied=False,
    )
    if named and any(allowed.roles_for(r) & named for r in readings):
        return True

    context = _roles_in_context(text, match.start(), match.end(), token=match.group(0))
    if not context:
        return False
    # The metric veto, and the one thing that overrides it. A claim statement names the metric
    # it is about, so "the revenue-growth claim was supported at 95% confidence" mentions a
    # column and is still a statement about a confidence, not a measurement. An explicit
    # confidence *word* says which of the two it is; "net margin deteriorated by 5%" has no
    # such word and stays refused.
    if "confidence" not in context or not _CONFIDENCE_WORD.search(
        _window_around(text, match.start(), match.end())
    ):
        if allowed.mentions_a_metric(_window_around(text, match.start(), match.end())):
            return False
    return any(allowed.roles_for(r) & context for r in readings)


def verify_narrative(text: str, allowed: AllowedFigures) -> str | None:
    """
    ``text`` when every figure in it is one the run recorded, in the role the prose gives it;
    otherwise ``None``.

    Returning ``None`` rather than a repaired string is the point: the caller has a true
    statement to fall back to, and a narrative that has been edited to remove a lie is not
    the narrative the model produced.
    """
    cleaned = text.strip()
    if not cleaned:
        return None

    ratio = _RATIO_CLAIMS.search(cleaned)
    if ratio is not None:
        # A ratio the run never computed is a fabricated figure whether or not it is spelled
        # with digits, so it costs the narrative exactly as a bad number would.
        return None

    for token in _NUMERIC.finditer(cleaned):
        if not _digit_checks_out(cleaned, token, allowed):
            return None

    # Number words: recorded somewhere, but not held to the role the prose puts them in.
    # See "Digits are held to a stricter standard than number words" in the module docstring.
    for token in _WORD_RE.finditer(cleaned):
        if not allowed.any_role_has(_WORD_NUMBERS[token.group(0).lower()]):
            return None

    return cleaned
