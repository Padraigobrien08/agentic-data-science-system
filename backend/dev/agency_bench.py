"""
Run ``suite_agency_v1`` against real models and produce a publishable scoreboard.

The agency suite scores whether the investigation loop *reasons* well — concludes when the
evidence supports it, revises when contradicted, declines when it cannot. It was written to
accept any :class:`~agentic.agent.policy.AgentPolicy` precisely so a model could be held to the
same bar as the deterministic baseline. This is the harness that does that.

It lives in ``backend/dev`` rather than in ``agentic/evaluation`` on purpose: assembling a
model-backed policy requires settings, a provider, and the prompt registry, and ``agentic/``
must not import any of them. Keeping the coupling here is what lets
``python -m agentic.evaluation`` stay offline, free, and deterministic.

Usage::

    # deterministic baseline, no provider needed
    python -m backend.dev.agency_bench --policy fixture --trials 3

    # baseline plus a model, under a suite-level cost ceiling
    python -m backend.dev.agency_bench \\
        --policy fixture --policy model --model gpt-5.4-mini \\
        --trials 5 --max-cost-usd 2.00 --out scoreboard --format both

Model rows need a configured provider (``EDGAR_BACKEND_OPENAI_API_KEY`` or
``OPENAI_API_KEY``). Without one, ``build_agent_policy`` degrades to the fixture policy — the
harness detects that and says so rather than reporting a fixture result under a model's name.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from pathlib import Path

import structlog

from agentic.agent.budget import LoopBudget
from agentic.agent.policy import AgentPolicy
from agentic.evaluation.agency import AgencyReport
from agentic.evaluation.cases import SUITE_ID
from agentic.evaluation.runner import run_agency_suite
from agentic.evaluation.scoreboard import (
    MetricsObserver,
    PolicyScorecard,
    RunMetrics,
    Scoreboard,
    aggregate_trials,
)
from backend.agents.agentic_model_policy import AGENTIC_PROMPT_VERSION, build_agent_policy
from backend.config.settings import Settings, get_settings

log = structlog.get_logger(__name__)

FIXTURE = "fixture"
MODEL = "model"

#: Returns the policy for one row. Injectable so tests never construct a provider.
PolicyFactory = Callable[[str, Settings], AgentPolicy]


def _default_policy_factory(kind: str, settings: Settings) -> AgentPolicy:
    if kind == FIXTURE:
        from agentic.agent.fixture_policy import FixtureAgentPolicy

        return FixtureAgentPolicy()
    return build_agent_policy(settings)


def _label(kind: str, model: str | None) -> str:
    return FIXTURE if kind == FIXTURE else (model or "model")


def run_policy_rows(
    kinds: list[str],
    *,
    model: str | None = None,
    trials: int = 3,
    max_cost_usd: float | None = None,
    budget_cost_usd: float | None = None,
    settings: Settings | None = None,
    policy_factory: PolicyFactory = _default_policy_factory,
) -> list[PolicyScorecard]:
    """
    Run the suite ``trials`` times per requested policy and aggregate one scorecard each.

    Trials stop early — and the row is marked ``truncated`` — once accumulated spend crosses
    ``max_cost_usd``. That ceiling sits on top of the per-run ``LoopBudget.max_cost_usd``:
    the budget bounds one investigation, this bounds the whole benchmark.
    """
    base = settings if settings is not None else get_settings()
    rows: list[PolicyScorecard] = []

    for kind in kinds:
        row_settings = base.model_copy(update={"agent_completion_model": model}) if (
            kind == MODEL and model
        ) else base
        policy = policy_factory(kind, row_settings)
        label = _label(kind, model)

        if kind == MODEL and type(policy).__name__ == "FixtureAgentPolicy":
            # Reporting a fixture result under a model's name would silently corrupt the
            # scoreboard's central claim, so refuse the row instead.
            log.error("agency_bench.no_provider", label=label)
            raise SystemExit(
                f"--policy model requested for {label!r} but no LLM provider is configured; "
                "set EDGAR_BACKEND_OPENAI_API_KEY (or OPENAI_API_KEY) or drop the model row."
            )

        budget = LoopBudget(max_cost_usd=budget_cost_usd) if budget_cost_usd else None
        reports: list[AgencyReport] = []
        metrics: list[RunMetrics] = []
        truncated = False

        for trial in range(trials):
            observer = MetricsObserver()
            reports.append(run_agency_suite(policy=policy, observer=observer, budget=budget))
            metrics.extend(observer.drain())
            spent = sum(m.cost_usd for m in metrics)
            log.info(
                "agency_bench.trial",
                label=label,
                trial=trial + 1,
                of=trials,
                pass_rate=reports[-1].pass_rate,
                spent_usd=round(spent, 4),
            )
            if max_cost_usd is not None and spent >= max_cost_usd and trial + 1 < trials:
                log.warning(
                    "agency_bench.cost_ceiling",
                    label=label,
                    spent_usd=round(spent, 4),
                    ceiling_usd=max_cost_usd,
                    completed_trials=trial + 1,
                    requested_trials=trials,
                )
                truncated = True
                break

        rows.append(aggregate_trials(label, reports, metrics, truncated=truncated))

    return rows


def _render_json(board: Scoreboard, *, trials: int, model: str | None) -> str:
    payload = {
        "suite_id": board.suite_id,
        "prompt_version": AGENTIC_PROMPT_VERSION,
        "requested_trials": trials,
        "model": model,
        "rows": [row.model_dump(mode="json") for row in board.rows],
    }
    return json.dumps(payload, indent=2, sort_keys=True)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="python -m backend.dev.agency_bench",
        description="Score policies on suite_agency_v1 over repeated trials.",
    )
    p.add_argument(
        "--policy",
        action="append",
        choices=[FIXTURE, MODEL],
        help="Policy row to measure; repeat to compare (default: fixture).",
    )
    p.add_argument("--model", default=None, help="Model id for the 'model' row.")
    p.add_argument(
        "--trials",
        type=int,
        default=3,
        help="Suite runs per policy. More than one is required for a model row to mean anything.",
    )
    p.add_argument(
        "--max-cost-usd",
        type=float,
        default=None,
        help="Suite-level spend ceiling; remaining trials are skipped once crossed.",
    )
    p.add_argument(
        "--budget-cost-usd",
        type=float,
        default=None,
        help="Per-investigation LoopBudget.max_cost_usd.",
    )
    p.add_argument("--out", default=None, help="Path stem for written output (no extension).")
    p.add_argument("--format", choices=["json", "md", "both"], default="md")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    kinds = args.policy or [FIXTURE]
    if args.trials < 1:
        raise SystemExit("--trials must be at least 1")

    rows = run_policy_rows(
        kinds,
        model=args.model,
        trials=args.trials,
        max_cost_usd=args.max_cost_usd,
        budget_cost_usd=args.budget_cost_usd,
    )
    board = Scoreboard(suite_id=SUITE_ID, rows=rows)

    markdown = board.to_markdown()
    payload = _render_json(board, trials=args.trials, model=args.model)

    if args.format in ("md", "both"):
        print(markdown)
    if args.format == "json":
        print(payload)

    if args.out:
        stem = Path(args.out)
        if args.format in ("md", "both"):
            stem.with_suffix(".md").write_text(markdown + "\n", encoding="utf-8")
        if args.format in ("json", "both"):
            stem.with_suffix(".json").write_text(payload + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
