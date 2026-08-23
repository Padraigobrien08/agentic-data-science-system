"""
The guard that lets the loop write prose without letting it state figures.

These are the tests that keep "no number in a trace originates from a language model" true
once a model is allowed to write sentences. They are mostly about rejection: a narrative is
only useful if the reader can trust every figure in it, so the interesting cases are the
ones that must not get through.
"""

from __future__ import annotations

from agentic.agent.narrative import AllowedNumbers, extract_numbers, verify_narrative


def allowed(*, counts: list[int] | None = None, confidences: list[float] | None = None):
    a = AllowedNumbers()
    for c in counts or []:
        a.add_count(c)
    for c in confidences or []:
        a.add_confidence(c)
    return a


def test_prose_with_no_figures_passes_through() -> None:
    a = allowed()
    assert verify_narrative("The claim held under the evidence available.", a) == (
        "The claim held under the evidence available."
    )


def test_a_recorded_count_is_allowed() -> None:
    a = allowed(counts=[73])
    assert verify_narrative("Across 73 evidence items, it held.", a) is not None


def test_a_count_the_run_never_recorded_is_rejected() -> None:
    # The whole point: 74 is plausible, adjacent to the truth, and wrong.
    a = allowed(counts=[73])
    assert verify_narrative("Across 74 evidence items, it held.", a) is None


def test_confidence_is_admitted_as_a_fraction_or_a_percentage() -> None:
    a = allowed(confidences=[0.95])
    assert verify_narrative("It held at 95%.", a) is not None
    assert verify_narrative("It held at 0.95 confidence.", a) is not None
    assert verify_narrative("It held at 95 percent.", a) is not None


def test_a_confidence_that_was_rounded_up_is_rejected() -> None:
    a = allowed(confidences=[0.95])
    assert verify_narrative("It held at 96%.", a) is None


def test_one_bad_figure_invalidates_the_whole_narrative() -> None:
    # No partial trust: a paragraph with one invented number is not two-thirds true.
    a = allowed(counts=[2, 73], confidences=[0.95])
    text = "Both claims held at 95% across 73 evidence items, over 12 quarters."
    assert verify_narrative(text, a) is None


def test_number_words_are_checked_like_digits() -> None:
    a = allowed(counts=[2])
    assert verify_narrative("Both claims held.", a) is not None
    assert verify_narrative("Three claims held.", a) is None


def test_none_and_no_are_treated_as_zero() -> None:
    a = allowed(counts=[0])
    assert verify_narrative("No claim survived the evidence.", a) is not None


def test_thousands_separators_are_understood() -> None:
    a = allowed(counts=[1200])
    assert verify_narrative("It scanned 1,200 rows.", a) is not None
    assert verify_narrative("It scanned 1,300 rows.", a) is None


def test_empty_or_whitespace_prose_is_not_an_answer() -> None:
    a = allowed()
    assert verify_narrative("", a) is None
    assert verify_narrative("   \n ", a) is None


def test_surrounding_whitespace_is_trimmed_not_rejected() -> None:
    a = allowed()
    assert verify_narrative("  It held.  ", a) == "It held."


def test_extract_numbers_sees_digits_and_words() -> None:
    found = extract_numbers("Both claims held at 95% across 73 items.")
    assert "95%" in found
    assert "73" in found
    assert "both" in found


def test_counts_gathered_from_a_mapping() -> None:
    a = AllowedNumbers().add_many_counts({"hypotheses": 2, "evidence": 73})
    assert verify_narrative("2 claims, 73 items.", a) is not None
    assert verify_narrative("3 claims.", a) is None


def test_booleans_in_a_count_mapping_are_not_admitted_as_numbers() -> None:
    # `True` is an int in Python; admitting it would silently allow the figure 1.
    a = AllowedNumbers().add_many_counts({"converged": True})
    assert verify_narrative("It ran 1 experiment.", a) is None
