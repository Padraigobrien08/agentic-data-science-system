"""
The guard that lets the loop write prose without letting it state figures.

These are the tests that keep "no number in a trace originates from a language model" true
once a model is allowed to write sentences. They are mostly about rejection: a narrative is
only useful if the reader can trust every figure in it, so the interesting cases are the
ones that must not get through.

Figures are admitted **per role** — a count of evidence is sayable in a clause about evidence
and nowhere else — so every fixture here names the role it is granting. The adversarial cases
that motivated that design, and the corpus of real narratives that keeps it from over-tightening,
live in ``tests/agentic/test_narrative_verifier.py``.
"""

from __future__ import annotations

from agentic.agent.narrative import AllowedFigures, extract_numbers, verify_narrative


def allowed(**by_role: object) -> AllowedFigures:
    """``allowed(evidence=[73], confidence=[0.95])`` — values granted under named roles."""
    figures = AllowedFigures()
    for role, values in by_role.items():
        for value in values:  # type: ignore[union-attr]
            if role == "confidence":
                figures.add_confidence(float(value))
            else:
                figures.add(role, value)
    return figures


def test_prose_with_no_figures_passes_through() -> None:
    a = allowed()
    assert verify_narrative("The claim held under the evidence available.", a) == (
        "The claim held under the evidence available."
    )


def test_a_recorded_count_is_allowed() -> None:
    a = allowed(evidence=[73])
    assert verify_narrative("Across 73 evidence items, it held.", a) is not None


def test_a_count_the_run_never_recorded_is_rejected() -> None:
    # The whole point: 74 is plausible, adjacent to the truth, and wrong.
    a = allowed(evidence=[73])
    assert verify_narrative("Across 74 evidence items, it held.", a) is None


def test_a_recorded_count_spent_as_the_wrong_quantity_is_rejected() -> None:
    """
    The hole this design closes. 73 is a real count of evidence items; it is not a number of
    experiments, and prose that says it is has invented a figure out of a true one.
    """
    a = allowed(evidence=[73])
    assert verify_narrative("It ran 73 experiments.", a) is None


def test_an_unlabelled_figure_is_rejected_even_when_recorded() -> None:
    """A number with nothing saying what it counts cannot be checked, so it is not kept."""
    a = allowed(evidence=[73])
    assert verify_narrative("There were 73 of them.", a) is None


def test_confidence_is_admitted_as_a_fraction_or_a_percentage() -> None:
    a = allowed(confidence=[0.95])
    assert verify_narrative("It held at 95%.", a) is not None
    assert verify_narrative("It held at 0.95 confidence.", a) is not None
    assert verify_narrative("It held at 95 percent.", a) is not None


def test_a_confidence_that_was_rounded_up_is_rejected() -> None:
    a = allowed(confidence=[0.95])
    assert verify_narrative("It held at 96%.", a) is None


def test_one_bad_figure_invalidates_the_whole_narrative() -> None:
    # No partial trust: a paragraph with one invented number is not two-thirds true.
    a = allowed(hypotheses=[2], evidence=[73], confidence=[0.95])
    text = "Both claims held at 95% across 73 evidence items, over 12 quarters."
    assert verify_narrative(text, a) is None


def test_number_words_are_checked_against_recorded_values() -> None:
    a = allowed(hypotheses=[2])
    assert verify_narrative("Both claims held.", a) is not None
    assert verify_narrative("Three claims held.", a) is None


def test_function_words_are_not_read_as_figures() -> None:
    # Learned from real output: checking "no" and "one" as numerals discarded five of eight
    # recorded narratives, almost all over an ordinary negation. Prose has to survive its own
    # vocabulary — the strictness that matters is on digits.
    a = allowed(hypotheses=[2])

    assert verify_narrative("There was no decisive confirmation either way.", a) is not None
    assert verify_narrative("The stronger one could not be identified.", a) is not None
    assert verify_narrative("Neither claim held, and one of the two was weakened.", a) is not None


def test_number_words_are_not_held_to_a_role() -> None:
    """
    Deliberate asymmetry. "signs pointing in both directions" is idiom, not a count of
    anything the findings carry, and role-checking it discarded four of the seven narratives
    this loop has produced. A fabricated statistic is written in digits; those stay strict.
    """
    a = allowed(hypotheses=[2])
    assert verify_narrative("The evidence pointed in both directions.", a) is not None


def test_a_true_zero_is_still_sayable() -> None:
    # A claim with nothing against it has zero refuting items, and the run knows it.
    a = allowed(supporting_evidence=[3], refuting_evidence=[0])
    assert verify_narrative("It was carried by 3 supporting items with 0 against.", a) is not None


def test_thousands_separators_are_understood() -> None:
    a = allowed(rows=[1200])
    assert verify_narrative("It scanned 1,200 rows.", a) is not None
    assert verify_narrative("It scanned 1,300 rows.", a) is None


def test_the_sign_is_part_of_the_figure() -> None:
    """A recorded rise does not license a reported fall of the same magnitude."""
    a = allowed(rows=[5])
    assert verify_narrative("It moved by -5 rows.", a) is None


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
    a = AllowedFigures().add_counts({"hypotheses": 2, "evidence": 73})
    assert verify_narrative("2 claims, 73 evidence items.", a) is not None
    assert verify_narrative("3 claims.", a) is None


def test_booleans_in_a_count_mapping_are_not_admitted_as_numbers() -> None:
    # `True` is an int in Python; admitting it would silently allow the figure 1.
    a = AllowedFigures().add_counts({"converged": True})
    assert verify_narrative("It ran 1 experiment.", a) is None


def test_a_figure_attached_to_a_dataset_column_is_never_kept() -> None:
    """
    The findings carry no measured values, so any figure the prose hangs on a metric is
    invented — including one that collides with a real confidence.
    """
    a = allowed(confidence=[0.05]).add_metric_terms(["net_margin", "revenue"])
    assert verify_narrative("Net margin deteriorated by 5% over the period.", a) is None
    # ...but an explicit confidence word says which quantity is meant, and that is honest.
    assert verify_narrative("The net-margin claim held at 5% confidence.", a) is not None
