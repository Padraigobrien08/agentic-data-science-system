"""
Adaptive investigation loop.

Ten explicit components (`components.py`) driven by an :class:`AgentPolicy`
(`policy.py`) over the deterministic experiment registry, orchestrated by
:class:`InvestigationLoop` (`loop.py`). Execution paths differ by goal,
intermediate results steer selection, hypotheses can be supported/weakened/
rejected/unresolved, budgets and safety limits bound the run, every decision is
persisted, and the loop is resumable.

See ``docs/agent/{investigation-loop,decision-policy,termination-policy}.md``.
Not yet wired into production orchestration.
"""

from __future__ import annotations

from .budget import BudgetTracker, LoopBudget, SafetyLimits
from .components import (
    ConclusionSynthesizer,
    Critic,
    EvidenceUpdater,
    ExperimentExecutor,
    ExperimentSelector,
    GoalInterpreter,
    HypothesisGenerator,
    HypothesisUpdater,
    InvestigationPlanner,
    TerminationPolicy,
)
from .fixture_policy import FixtureAgentPolicy
from .loop import InvestigationLoop, run_investigation
from .policy import (
    AgentPolicy,
    AgentPolicyError,
    AnalysisIntent,
    ExperimentChoice,
    GoalInterpretation,
    MalformedPolicyResponse,
    ModelAgentPolicy,
)
from .store import InMemoryInvestigationStore, InvestigationStore, NullInvestigationStore

__all__ = [
    "InvestigationLoop",
    "run_investigation",
    # policy
    "AgentPolicy",
    "FixtureAgentPolicy",
    "ModelAgentPolicy",
    "AgentPolicyError",
    "MalformedPolicyResponse",
    "AnalysisIntent",
    "GoalInterpretation",
    "ExperimentChoice",
    # components
    "GoalInterpreter",
    "HypothesisGenerator",
    "InvestigationPlanner",
    "ExperimentSelector",
    "ExperimentExecutor",
    "EvidenceUpdater",
    "HypothesisUpdater",
    "Critic",
    "TerminationPolicy",
    "ConclusionSynthesizer",
    # budgets / store
    "LoopBudget",
    "SafetyLimits",
    "BudgetTracker",
    "InvestigationStore",
    "InMemoryInvestigationStore",
    "NullInvestigationStore",
]
