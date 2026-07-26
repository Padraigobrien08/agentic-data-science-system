"""Supported evaluation-suite catalog for product-facing workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from edgar_project.evaluation.schemas import InputMode
from edgar_project.repo_layout import REPO_ROOT


@dataclass(frozen=True)
class SupportedEvaluationSuite:
    suite_id: str
    label: str
    primary_mode: InputMode
    manifest_path: Path
    description: str = ""


_BENCHMARK_ROOT = REPO_ROOT / "edgar_project" / "evaluation" / "benchmarks"
_SUITES: tuple[SupportedEvaluationSuite, ...] = (
    SupportedEvaluationSuite(
        suite_id="suite_fixtures_v1",
        label="Fixture Regression Suite",
        primary_mode=InputMode.fixture,
        manifest_path=_BENCHMARK_ROOT / "suite_fixtures_v1.json",
        description="Offline deterministic fixture suite used as the default regression path.",
    ),
    SupportedEvaluationSuite(
        suite_id="suite_smoke",
        label="Live Smoke Suite",
        primary_mode=InputMode.live,
        manifest_path=_BENCHMARK_ROOT / "suite_smoke.json",
        description="Operator-invoked live smoke scaffold with explicit fair-access policy.",
    ),
    SupportedEvaluationSuite(
        suite_id="suite_hybrid_smoke_v1",
        label="Hybrid Smoke Suite",
        primary_mode=InputMode.hybrid,
        manifest_path=_BENCHMARK_ROOT / "suite_hybrid_smoke_v1.json",
        description="Operator-invoked hybrid smoke scaffold with explicit fair-access policy.",
    ),
)
_SUITES_BY_ID = {suite.suite_id: suite for suite in _SUITES}


def list_supported_evaluation_suites() -> list[SupportedEvaluationSuite]:
    """Return the supported suite catalog in stable display order."""

    return list(_SUITES)


def get_supported_evaluation_suite(suite_id: str) -> SupportedEvaluationSuite:
    """Resolve one supported suite by stable ID."""

    try:
        return _SUITES_BY_ID[suite_id]
    except KeyError as exc:  # pragma: no cover - tiny guard
        raise KeyError(f"Unsupported evaluation suite: {suite_id}") from exc

