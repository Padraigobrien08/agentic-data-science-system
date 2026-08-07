"""
Agency evaluation — measuring whether the loop reasons well, not whether it runs.

The existing benchmark suites check *outputs*: did the pipeline produce the right artifacts
with the right numbers. That is necessary and stays unchanged. It says nothing about the
question an agentic system actually has to answer well: given evidence, does it draw the right
conclusion, revise when contradicted, and decline when the data cannot support a claim?

This module scores those properties. Every check is **deterministic** — derived from persisted
typed state, never from a model judging a model — so a case's verdict is reproducible and a
regression is unambiguous.

The scoring deliberately treats two opposite failures as equally bad:

* **Overclaiming** — asserting a trend in flat or noisy data, or confirming a hypothesis the
  evidence contradicts.
* **Underclaiming** — concluding "insufficient evidence" on an unambiguous signal. An agent
  that always hedges is never wrong and never useful, and a suite without positive controls
  would score it perfectly.
"""

from __future__ import annotations

from enum import Enum

from pydantic import Field

from agentic.domain import Investigation
from agentic.domain.common import DomainModel


class AgencyProperty(str, Enum):
    """The behaviors a competent investigation loop must exhibit."""

    terminates_for_the_right_reason = "terminates_for_the_right_reason"
    """Stops with the typed reason the evidence warrants."""

    reaches_the_right_disposition = "reaches_the_right_disposition"
    """Concludes supported / refuted / insufficient in line with the data."""

    revises_under_contradiction = "revises_under_contradiction"
    """A hypothesis the evidence opposes does not end up supported."""

    preserves_contradicting_evidence = "preserves_contradicting_evidence"
    """Opposing evidence is retained, not discarded in favour of a tidy story."""

    path_adapts_to_goal = "path_adapts_to_goal"
    """The experiments chosen reflect what was asked."""

    avoids_redundant_experiments = "avoids_redundant_experiments"
    """No tool is run twice for the same question."""

    respects_budget = "respects_budget"
    """Stays within the resource bounds it was given."""

    calibrated_confidence = "calibrated_confidence"
    """Confidence is proportional to the strength of the evidence."""

    challenges_before_concluding = "challenges_before_concluding"
    """A claim it accepted was first tested by an independent method it chose to run.

    This is the property that separates an adversarial loop from a pipeline that stops at the
    first agreeable result, and it needs its own name because the loop degrades *quietly*
    without it: a critic that never challenges still terminates ``sufficient_evidence`` once
    the candidate tools run out, reaching the same disposition at the same confidence by
    simply running everything. Only the presence of a critique whose falsification tool
    actually executed distinguishes the two.
    """


class AgencyExpectations(DomainModel):
    """Declarative, deterministic expectations for one case.

    Every field is optional; a case only asserts the properties it is designed to probe, so a
    fixture testing overclaiming does not accidentally assert things about tool choice.
    """

    termination_reason_in: list[str] = Field(default_factory=list)
    disposition_in: list[str] = Field(default_factory=list)
    #: Statuses no hypothesis may end in — e.g. ``["supported"]`` for a contradicted claim.
    hypothesis_status_not_in: list[str] = Field(default_factory=list)
    #: At least one hypothesis must end in one of these.
    hypothesis_status_any: list[str] = Field(default_factory=list)
    expect_any_tool: list[str] = Field(default_factory=list)
    forbid_tools: list[str] = Field(default_factory=list)
    require_contradicting_evidence: bool = False
    #: A supported conclusion must have been challenged by a critique whose suggested
    #: falsification tool actually ran. Only meaningful on cases that converge — a case
    #: expected to end ``insufficient`` has nothing to challenge.
    require_challenge: bool = False
    no_repeated_tools: bool = True
    max_experiments: int | None = None
    max_confidence: float | None = None
    min_confidence: float | None = None


class PropertyOutcome(DomainModel):
    """Whether one property held, and why not when it did not."""

    property: AgencyProperty
    passed: bool
    detail: str = ""


class AgencyCaseResult(DomainModel):
    case_id: str
    description: str = ""
    passed: bool
    outcomes: list[PropertyOutcome] = Field(default_factory=list)
    #: Observed facts, so a failure can be diagnosed without re-running the case.
    observed_termination: str | None = None
    observed_disposition: str | None = None
    observed_tools: list[str] = Field(default_factory=list)
    observed_hypothesis_statuses: list[str] = Field(default_factory=list)
    observed_confidence: float = 0.0
    #: Falsification tools that a critique proposed *and* the loop then ran.
    observed_challenge_tools: list[str] = Field(default_factory=list)

    @property
    def failures(self) -> list[PropertyOutcome]:
        return [o for o in self.outcomes if not o.passed]


class AgencyReport(DomainModel):
    """Suite-level result: overall pass rate plus a per-property breakdown."""

    suite_id: str
    total: int = 0
    passed: int = 0
    results: list[AgencyCaseResult] = Field(default_factory=list)

    @property
    def failed(self) -> int:
        return self.total - self.passed

    @property
    def pass_rate(self) -> float:
        return (self.passed / self.total) if self.total else 0.0

    def property_scores(self) -> dict[str, float]:
        """Pass rate per property, across the cases that asserted it.

        A per-property breakdown is what makes the suite diagnostic rather than a single
        number: "calibrated_confidence 0.4" points somewhere specific.
        """
        totals: dict[str, list[bool]] = {}
        for result in self.results:
            for outcome in result.outcomes:
                totals.setdefault(outcome.property.value, []).append(outcome.passed)
        return {
            name: round(sum(values) / len(values), 4)
            for name, values in sorted(totals.items())
            if values
        }

    def summary(self) -> str:
        line = f"{self.suite_id}: {self.passed}/{self.total} cases passed ({self.pass_rate:.0%})"
        if not self.failed:
            return line
        names = ", ".join(r.case_id for r in self.results if not r.passed)
        return f"{line} — failing: {names}"


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------


def _tools(investigation: Investigation) -> list[str]:
    return [r.tool_name for r in _results(investigation)]


def _statuses(investigation: Investigation) -> list[str]:
    return [h.status.value for h in investigation.state.hypotheses]


def _challenge_tools(investigation: Investigation) -> list[str]:
    """
    Falsification tools a critique proposed that were actually executed.

    A critique the loop never acted on is not a challenge — it is a note. This mirrors the
    ``tested`` condition in ``TerminationPolicy.decide``, so the property measures the same
    thing the loop itself treats as "this claim has been challenged".
    """
    executed = {r.tool_name for r in _results(investigation)}
    return sorted(
        {
            c.suggested_action
            for c in investigation.state.critiques
            if c.suggested_action and c.suggested_action in executed
        }
    )


def _results(investigation: Investigation):
    return investigation.state.completed_experiments + investigation.state.failed_experiments


def _check(
    prop: AgencyProperty, passed: bool, detail: str = "", outcomes: list[PropertyOutcome] | None = None
) -> None:
    if outcomes is not None:
        outcomes.append(PropertyOutcome(property=prop, passed=passed, detail="" if passed else detail))


def score_case(
    case_id: str, investigation: Investigation, expectations: AgencyExpectations, *, description: str = ""
) -> AgencyCaseResult:
    """Score one finished investigation against a case's expectations."""
    outcomes: list[PropertyOutcome] = []
    state = investigation.state

    termination = state.termination.reason.value if state.termination is not None else None
    conclusion = state.current_conclusion
    disposition = conclusion.disposition.value if conclusion is not None else None
    confidence = float(conclusion.confidence) if conclusion is not None else 0.0
    tools = _tools(investigation)
    statuses = _statuses(investigation)
    challenge_tools = _challenge_tools(investigation)

    if expectations.termination_reason_in:
        _check(
            AgencyProperty.terminates_for_the_right_reason,
            termination in expectations.termination_reason_in,
            f"terminated {termination!r}, expected one of {expectations.termination_reason_in}",
            outcomes,
        )

    if expectations.disposition_in:
        _check(
            AgencyProperty.reaches_the_right_disposition,
            disposition in expectations.disposition_in,
            f"concluded {disposition!r}, expected one of {expectations.disposition_in}",
            outcomes,
        )

    if expectations.hypothesis_status_not_in:
        offending = [s for s in statuses if s in expectations.hypothesis_status_not_in]
        _check(
            AgencyProperty.revises_under_contradiction,
            not offending,
            f"hypotheses ended {offending}, which the evidence does not support",
            outcomes,
        )

    if expectations.hypothesis_status_any:
        _check(
            AgencyProperty.revises_under_contradiction,
            any(s in expectations.hypothesis_status_any for s in statuses),
            f"hypotheses ended {statuses}, expected any of {expectations.hypothesis_status_any}",
            outcomes,
        )

    if expectations.require_contradicting_evidence:
        directions = {e.direction.value for e in state.evidence}
        _check(
            AgencyProperty.preserves_contradicting_evidence,
            "refutes" in directions,
            f"no refuting evidence retained; directions present: {sorted(directions)}",
            outcomes,
        )

    if expectations.require_challenge:
        _check(
            AgencyProperty.challenges_before_concluding,
            bool(challenge_tools),
            "concluded without testing the claim: "
            + (
                f"{len(state.critiques)} critique(s) raised but none of their falsification "
                f"tools ran (ran {tools})"
                if state.critiques
                else f"no critique was raised at all (ran {tools})"
            ),
            outcomes,
        )

    if expectations.expect_any_tool:
        _check(
            AgencyProperty.path_adapts_to_goal,
            any(t in expectations.expect_any_tool for t in tools),
            f"ran {tools}, expected at least one of {expectations.expect_any_tool}",
            outcomes,
        )

    if expectations.forbid_tools:
        used = [t for t in tools if t in expectations.forbid_tools]
        _check(
            AgencyProperty.path_adapts_to_goal,
            not used,
            f"ran {used}, which do not answer this goal",
            outcomes,
        )

    if expectations.no_repeated_tools:
        repeated = sorted({t for t in tools if tools.count(t) > 1})
        _check(
            AgencyProperty.avoids_redundant_experiments,
            not repeated,
            f"repeated experiments: {repeated}",
            outcomes,
        )

    if expectations.max_experiments is not None:
        _check(
            AgencyProperty.respects_budget,
            len(tools) <= expectations.max_experiments,
            f"ran {len(tools)} experiments, budget allowed {expectations.max_experiments}",
            outcomes,
        )

    if expectations.max_confidence is not None:
        _check(
            AgencyProperty.calibrated_confidence,
            confidence <= expectations.max_confidence,
            f"confidence {confidence:.2f} exceeds {expectations.max_confidence:.2f} for this evidence",
            outcomes,
        )

    if expectations.min_confidence is not None:
        _check(
            AgencyProperty.calibrated_confidence,
            confidence >= expectations.min_confidence,
            f"confidence {confidence:.2f} is below {expectations.min_confidence:.2f} "
            "despite an unambiguous signal",
            outcomes,
        )

    return AgencyCaseResult(
        case_id=case_id,
        description=description,
        passed=all(o.passed for o in outcomes),
        outcomes=outcomes,
        observed_termination=termination,
        observed_disposition=disposition,
        observed_tools=tools,
        observed_hypothesis_statuses=statuses,
        observed_confidence=round(confidence, 6),
        observed_challenge_tools=challenge_tools,
    )
