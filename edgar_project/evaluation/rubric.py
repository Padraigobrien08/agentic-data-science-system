"""Deterministic rubric primitives used by evaluation benchmarks."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from .schemas import RubricScore


class RubricCriterion(BaseModel):
    """Single deterministic criterion in a weighted rubric."""

    key: str
    description: str = ""
    weight: float = Field(default=1.0, ge=0.0)
    minimum: float | None = Field(
        default=None,
        description="Optional pass threshold for this criterion (normalized score)",
    )


class Rubric(BaseModel):
    """Rubric definition for deterministic benchmark scoring."""

    rubric_id: str = "deterministic_baseline_v1"
    pass_threshold: float = Field(
        default=0.8,
        ge=0.0,
        le=1.0,
        description="Required total normalized score to pass",
    )
    criteria: list[RubricCriterion] = Field(default_factory=list)

    def score(self, criterion_scores: dict[str, float]) -> RubricScore:
        """
        Aggregate criterion scores into a weighted normalized total.

        `criterion_scores` should use [0,1] values for deterministic checks.
        """

        if not self.criteria:
            return RubricScore(
                rubric_id=self.rubric_id,
                total_score=0.0,
                max_score=0.0,
                passed=False,
                details={},
            )

        max_score = sum(c.weight for c in self.criteria)
        weighted = 0.0
        details: dict[str, float] = {}
        for criterion in self.criteria:
            raw = float(criterion_scores.get(criterion.key, 0.0))
            clamped = max(0.0, min(1.0, raw))
            weighted += clamped * criterion.weight
            details[criterion.key] = clamped

        normalized = weighted / max_score if max_score > 0 else 0.0
        return RubricScore(
            rubric_id=self.rubric_id,
            total_score=normalized,
            max_score=1.0,
            passed=normalized >= self.pass_threshold,
            details=details,
        )

    @classmethod
    def from_json_file(cls, path: str | Path) -> Rubric:
        """Load rubric from a versioned JSON asset."""

        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.model_validate(payload)
