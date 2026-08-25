"""
Classifying how a run ended.

`status` is the wrong headline in the case that matters most: a run that correctly declined
is stored as `exhausted`, which reads as a failure. `outcome.kind` is the honest summary, and
it has to be derived from the termination reason, the claim statuses and the critique types
together — no single field carries it.

The cases below are the five published demos, which between them produce four distinct
outcomes; each `test_...` names the demo it was taken from.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from backend.schemas.investigation import _build_outcome


def _row(
    *,
    claims: list[str],
    reason: str | None,
    critiques: list[tuple[str, bool]] | None = None,
    conflict_pair: tuple[str, str] | None = None,
):
    """
    A stand-in investigation row: only the fields the classifier reads.

    Claims are addressable as ``hyp-0``, ``hyp-1``, … so a contradiction can name the two it
    is between. ``conflict_pair`` attaches that pairing to the first contradiction critique.
    """
    critique_rows = []
    for i, (kind, resolved) in enumerate(critiques or []):
        other = conflict_pair[1] if (conflict_pair and kind == "contradiction") else None
        target = conflict_pair[0] if (conflict_pair and kind == "contradiction") else f"hyp-{i}"
        critique_rows.append(
            SimpleNamespace(
                critique_type=kind, resolved=resolved,
                target_id=target, conflicts_with_id=other,
            )
        )
    return SimpleNamespace(
        hypotheses=[
            SimpleNamespace(domain_id=f"hyp-{i}", status=s) for i, s in enumerate(claims)
        ],
        termination_json={"reason": reason} if reason else {},
        critiques=critique_rows,
    )


def test_all_claims_standing_is_supported() -> None:
    """edgar-peer-separation: two supported claims, sufficient_evidence."""
    out = _build_outcome(_row(claims=["supported", "supported"], reason="sufficient_evidence"))

    assert out.kind == "supported"
    assert out.claims_supported == 2
    assert out.termination_reason == "sufficient_evidence"


def test_one_standing_and_one_overturned_is_mixed() -> None:
    """edgar-margin-vs-growth: the run that found one thing true and another false."""
    out = _build_outcome(_row(claims=["rejected", "supported"], reason="sufficient_evidence"))

    assert out.kind == "mixed"
    assert (out.claims_supported, out.claims_rejected) == (1, 1)


def test_nothing_standing_is_declined() -> None:
    """csv-delivery-delays: both claims weakened, insufficient_evidence."""
    out = _build_outcome(_row(claims=["weakened", "weakened"], reason="insufficient_evidence"))

    assert out.kind == "declined"
    assert out.claims_supported == 0


def test_every_claim_overturned_is_refuted_not_declined() -> None:
    """
    edgar-margin-vs-growth: the run's own evidence rejected both explanations it raised.

    Distinct from `declined`, and the distinction is not pedantic. "No claim survived the
    evidence" describes a run that could not settle the matter; this run settled it, and the
    answer was no to both. Reporting the strongest thing an investigation can do — disproving
    its own hypotheses — as a failure to conclude gets the result exactly backwards.
    """
    out = _build_outcome(_row(claims=["rejected", "rejected"], reason="insufficient_evidence"))

    assert out.kind == "refuted"
    assert out.claims_rejected == 2


def test_a_rejected_claim_beside_an_unsettled_one_is_still_declined() -> None:
    """`refuted` means *every* claim was overturned; a leftover unresolved claim is not that."""
    out = _build_outcome(_row(claims=["rejected", "unresolved"], reason="insufficient_evidence"))

    assert out.kind == "declined"


def test_an_untested_claim_still_counts_as_declined() -> None:
    """csv-regional-ranking: one unresolved, one weakened."""
    out = _build_outcome(_row(claims=["unresolved", "weakened"], reason="insufficient_evidence"))

    assert out.kind == "declined"
    assert out.claims_unresolved == 1


def test_a_contradiction_outranks_everything_else() -> None:
    """
    csv-staffing-vs-service.

    Ordered first on purpose: a run holding two claims that cannot both be true has not
    concluded anything, whatever the rest of its claims say.
    """
    out = _build_outcome(_row(
        claims=["weakened", "weakened"],
        reason="insufficient_evidence",
        critiques=[("competing_explanation", False), ("contradiction", False)],
    ))

    assert out.kind == "contradicted"
    assert out.contradiction_found is True


def test_a_contradiction_beats_standing_claims() -> None:
    """Even with a claim still supported, the conflict is the headline."""
    out = _build_outcome(_row(
        claims=["supported", "weakened"],
        reason="sufficient_evidence",
        critiques=[("contradiction", False)],
    ))

    assert out.kind == "contradicted"


def test_a_resolved_contradiction_no_longer_dominates() -> None:
    """Resolved means it was settled; the run should be judged on its claims again."""
    out = _build_outcome(_row(
        claims=["supported", "supported"],
        reason="sufficient_evidence",
        critiques=[("contradiction", True)],
    ))

    assert out.kind == "supported"
    assert out.contradiction_found is False


def test_a_contradiction_the_evidence_separated_is_read_as_settled() -> None:
    """
    Historical rows, written before the loop maintained ``resolved`` itself, carry
    ``resolved=False`` on conflicts the evidence plainly settled — because nothing ever set
    the flag. Judging by the claims recovers the truth: exactly one of the pair standing means
    the run answered the question it was holding open.
    """
    out = _build_outcome(_row(
        claims=["supported", "rejected"],
        reason="sufficient_evidence",
        critiques=[("contradiction", False)],
        conflict_pair=("hyp-0", "hyp-1"),
    ))

    assert out.contradiction_found is False
    assert out.kind == "mixed"


def test_an_unpaired_contradiction_is_still_treated_as_live() -> None:
    """Nothing can show a conflict was settled if its second side was never recorded."""
    out = _build_outcome(_row(
        claims=["supported", "rejected"],
        reason="sufficient_evidence",
        critiques=[("contradiction", False)],
    ))

    assert out.contradiction_found is True
    assert out.kind == "contradicted"


def test_a_question_the_data_cannot_answer_is_its_own_outcome() -> None:
    """
    csv-unanswerable-moat. Distinct from `declined`: that one says the evidence did not settle
    it, which invites more analysis. This says no analysis of *this* data would help.
    """
    out = _build_outcome(_row(claims=[], reason="unanswerable_premise"))

    assert out.kind == "unanswerable"
    assert out.termination_reason == "unanswerable_premise"


def test_unanswerable_outranks_a_stopped_reason() -> None:
    out = _build_outcome(_row(claims=["unresolved"], reason="unanswerable_premise"))

    assert out.kind == "unanswerable"


@pytest.mark.parametrize(
    "reason", ["budget_exhausted", "safety_constraint", "repeated_failure", "user_stop"]
)
def test_being_cut_off_is_not_a_verdict(reason: str) -> None:
    """A run that ran out of budget did not decide anything — that is not the same as declining."""
    out = _build_outcome(_row(claims=["supported"], reason=reason))

    assert out.kind == "stopped"
    assert out.termination_reason == reason


def test_a_run_with_no_claims_at_all_is_declined() -> None:
    out = _build_outcome(_row(claims=[], reason="no_valid_experiment"))

    assert out.kind == "declined"
    assert out.claims_supported == 0


def test_a_missing_termination_block_does_not_raise() -> None:
    """Persisted state is not guaranteed complete; classification must still produce something."""
    out = _build_outcome(_row(claims=["supported"], reason=None))

    assert out.kind == "supported"
    assert out.termination_reason is None
