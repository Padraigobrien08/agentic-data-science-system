"""
Explicit budgets and deterministic safety limits for the investigation loop.

Budgets bound resource usage (experiments, model calls, elapsed time, estimated
cost, repeated-tool usage). Safety limits are hard caps that must never be
exceeded regardless of budgets (max iterations, consecutive failures).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import Field

from agentic.domain.common import DomainModel


class LoopBudget(DomainModel):
    """Resource budget for one investigation run."""

    max_experiments: int = Field(default=8, ge=1)
    max_model_calls: int = Field(default=40, ge=1)
    max_elapsed_seconds: float = Field(default=120.0, gt=0)
    max_cost_usd: float = Field(default=1.0, gt=0)
    max_repeated_tool_uses: int = Field(default=3, ge=1)


class SafetyLimits(DomainModel):
    """Deterministic hard caps (independent of budgets)."""

    max_iterations: int = Field(default=25, ge=1)
    max_consecutive_failures: int = Field(default=3, ge=1)
    absolute_max_elapsed_seconds: float = Field(default=600.0, gt=0)


@dataclass
class BudgetTracker:
    """Live usage counters for one run (not serialized; loop-transient)."""

    budget: LoopBudget
    safety: SafetyLimits
    experiments_used: int = 0
    model_calls_used: int = 0
    cost_used_usd: float = 0.0
    elapsed_seconds: float = 0.0
    consecutive_failures: int = 0
    tool_uses: dict[str, int] = field(default_factory=dict)
    user_stop_requested: bool = False

    def record_model_call(self) -> None:
        self.model_calls_used += 1

    def record_experiment(self, tool_name: str, *, cost: float = 0.0, failed: bool = False) -> None:
        self.experiments_used += 1
        self.cost_used_usd += cost
        self.tool_uses[tool_name] = self.tool_uses.get(tool_name, 0) + 1
        self.consecutive_failures = self.consecutive_failures + 1 if failed else 0

    def tool_at_limit(self, tool_name: str) -> bool:
        return self.tool_uses.get(tool_name, 0) >= self.budget.max_repeated_tool_uses

    # -- limit checks --------------------------------------------------------

    def budget_exhausted(self) -> bool:
        return (
            self.experiments_used >= self.budget.max_experiments
            or self.model_calls_used >= self.budget.max_model_calls
            or self.elapsed_seconds >= self.budget.max_elapsed_seconds
            or self.cost_used_usd >= self.budget.max_cost_usd
        )

    def safety_violated(self, iterations: int) -> bool:
        return (
            iterations >= self.safety.max_iterations
            or self.elapsed_seconds >= self.safety.absolute_max_elapsed_seconds
        )

    def repeated_failure(self) -> bool:
        return self.consecutive_failures >= self.safety.max_consecutive_failures
