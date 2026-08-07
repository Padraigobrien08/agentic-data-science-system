"""
Agency evaluation for the investigation loop.

Measures whether the loop *reasons* well — concludes when the evidence supports it, revises
when contradicted, declines when it cannot — as opposed to the output-oriented benchmark
suites in ``edgar_project/evaluation``. Every check is deterministic and offline.
"""

from .agency import (
    AgencyCaseResult,
    AgencyExpectations,
    AgencyProperty,
    AgencyReport,
    PropertyOutcome,
    score_case,
)
from .cases import AGENCY_CASES, SUITE_ID, AgencyCase
from .fixtures import FIXTURES, build_fixture
from .runner import format_report, run_agency_suite, run_case
from .scoreboard import (
    CaseStability,
    MetricsObserver,
    PolicyScorecard,
    RunMetrics,
    Scoreboard,
    aggregate_trials,
)

__all__ = [
    "AgencyProperty",
    "AgencyExpectations",
    "PropertyOutcome",
    "AgencyCaseResult",
    "AgencyReport",
    "score_case",
    "AgencyCase",
    "AGENCY_CASES",
    "SUITE_ID",
    "FIXTURES",
    "build_fixture",
    "run_case",
    "run_agency_suite",
    "format_report",
    # multi-trial aggregation
    "RunMetrics",
    "MetricsObserver",
    "CaseStability",
    "PolicyScorecard",
    "Scoreboard",
    "aggregate_trials",
]
