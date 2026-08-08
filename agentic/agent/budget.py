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

    max_experiments: int = Field(
        default=8,
        ge=1,
        description=(
            "Experiments the whole investigation may run. This scales with the number of "
            "hypotheses, not just the goal's difficulty: each claim draws its own candidates, "
            "parameterised to its own metric. Measured against the deterministic policy, one "
            "claim costs 2, two cost 3, three cost 7, and four reach this cap and terminate "
            "`budget_exhausted`. Left at 8 so a realistic multi-part question (two or three "
            "clauses) completes by default while a runaway one stops with a typed reason "
            "rather than silently. Raise it if you routinely ask four-part questions — it "
            "raises worst-case cost and latency proportionally."
        ),
    )
    max_parallel_experiments: int = Field(
        default=1,
        ge=1,
        description=(
            "Experiments the loop may run concurrently within one iteration. 1 (default) is "
            "strictly sequential. Higher values trade some adaptivity — later experiments in a "
            "batch are chosen without seeing the earlier ones' results — for latency and fewer "
            "selector model calls. Results are always folded back in selection order, so the "
            "resulting state is identical to running the batch sequentially."
        ),
    )
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

    def record_model_cost(self, cost: float) -> None:
        """Attribute spend to the run. Separate from the count so a model call that
        raises is still counted while its (possibly zero) cost is attributed after."""
        if cost > 0:
            self.cost_used_usd += cost

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
