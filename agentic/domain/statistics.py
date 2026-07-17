"""
Statistical summary value objects.

Typed carriers for the statistical backing of an observation or evidence record:
sample size, effect size, uncertainty, assumptions, diagnostics, coverage, and
warnings. These are the "evidence strength inputs" that deterministic experiments
emit and that an evidence updater maps to bounded strength/reliability/coverage.
"""

from __future__ import annotations

from pydantic import Field

from .common import DOMAIN_SCHEMA_VERSION, DomainModel


class Uncertainty(DomainModel):
    """Uncertainty around a point estimate (confidence interval / standard error)."""

    confidence_level: float | None = Field(default=None, ge=0.0, le=1.0)
    ci_low: float | None = Field(default=None)
    ci_high: float | None = Field(default=None)
    std_error: float | None = Field(default=None, ge=0.0)


class StatisticalSummary(DomainModel):
    """The statistical backing of a computed result (all fields optional)."""

    sample_size: int | None = Field(default=None, ge=0)
    effect_size: float | None = Field(default=None)
    effect_size_kind: str | None = Field(
        default=None,
        description="Name of the effect-size measure, e.g. cohens_d, pearson_r, slope, cramers_v.",
    )
    p_value: float | None = Field(default=None, ge=0.0, le=1.0)
    uncertainty: Uncertainty | None = Field(default=None)
    assumptions: list[str] = Field(default_factory=list)
    diagnostics: dict[str, float] = Field(default_factory=dict)
    coverage: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Fraction of the relevant scope the result spans (non-null / in-scope).",
    )
    warnings: list[str] = Field(default_factory=list)
    schema_version: str = Field(default=DOMAIN_SCHEMA_VERSION)
