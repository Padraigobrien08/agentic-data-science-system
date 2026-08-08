#!/usr/bin/env python3
"""
Drive varied agent activity against a running local stack, to populate the agent-loop dashboard.

The dashboard in ``ops/grafana/dashboards/agent-loop.json`` has 13 panels, 7 of them timeseries,
with 16 targets using ``rate()`` at a 15s scrape. A handful of investigations produces a
technically correct and completely uninformative picture. This script supplies the sustained,
*varied* workload the panels were designed to read.

Variety is the point, not volume. ``docs/observability.md`` names the signatures the dashboard
exposes — median iterations pinned at 1 means the loop is not iterating, a flat single-tool
profile means it is not adapting, only ``-> supported`` transitions mean it is never challenged.
A workload of one repeated goal reproduces all three and would make the instrumentation look
broken. So the catalogue below spans intents, and deliberately includes goals the data cannot
support, so terminations and error panels are exercised too.

**Free and offline by construction.** ``build_agent_policy`` falls back to
``FixtureAgentPolicy`` when no LLM provider is configured, and the fixture policy still drives
every ``edgar_agent_*`` metric — components, experiments, hypothesis transitions, terminations.
Datasets are small in-memory CSVs rendered from ``agentic.evaluation.fixtures``; nothing reaches
SEC or any other external service.

The one caveat: on a machine that *does* have a provider configured, the backend will use the
model policy and these runs will cost money. That is the operator's standing configuration, not
something this script turns on — unset ``EDGAR_BACKEND_OPENAI_API_KEY`` for the api and worker
if you want the guarantee.

Usage::

    docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
    python3 scripts/seed-agent-activity.py --duration 1800

Requires ``EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true`` on both the api and the worker, and
``EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=true`` unless you pass credentials for an existing user.
See "Populating the dashboard" in ``docs/observability.md``.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import Counter
from dataclasses import dataclass, field

import requests

from agentic.evaluation.fixtures import build_fixture

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


@dataclass(frozen=True)
class SeedGoal:
    """One question over one fixture, plus the structural hints the adapter needs."""

    goal: str
    fixture_id: str
    time_field: str | None
    entity_id_fields: list[str] = field(default_factory=list)
    #: Why this entry is in the catalogue — which panel it is here to exercise.
    exercises: str = ""

    def csv(self) -> str:
        return build_fixture(self.fixture_id).to_csv(index=False)


#: Spans intents on purpose. A catalogue that only asked trend questions would produce exactly
#: the flat single-tool profile the dashboard flags as "the loop is not adapting".
GOAL_CATALOGUE: tuple[SeedGoal, ...] = (
    # -- converging trends: the happy path, and the bulk of the tool mix ----------
    SeedGoal("value is increasing over time", "clear_rising", "period", ["entity"],
             exercises="trend tools; supported transitions"),
    SeedGoal("value is decreasing over time", "clear_falling", "period", ["entity"],
             exercises="trend tools in the other direction"),
    SeedGoal("rainfall_mm is increasing over time", "rainfall_rising", "month", ["station"],
             exercises="trend over non-financial vocabulary"),
    # -- non-convergence: without these the termination breakdown is one slice ----
    SeedGoal("value is increasing over time", "flat", "period", ["entity"],
             exercises="insufficient_evidence terminations"),
    SeedGoal("value is increasing over time", "noisy_no_trend", "period", ["entity"],
             exercises="weakened hypotheses; refuting evidence"),
    SeedGoal("value is increasing over time", "too_short", "period", ["entity"],
             exercises="no_valid_experiment / short-data handling"),
    SeedGoal("latency_ms is increasing over time", "response_latency_flat", "day", ["service"],
             exercises="a flat non-financial series"),
    # -- other intents: this is what stops the tool mix being degenerate ---------
    SeedGoal("does value differ between groups?", "separated_groups", "period", ["entity"],
             exercises="compare_groups"),
    SeedGoal("which entity has the highest value?", "opposing_entities", "period", ["entity"],
             exercises="rank_entities"),
    SeedGoal("are there unusual values in value?", "noisy_no_trend", "period", ["entity"],
             exercises="detect_outliers"),
    SeedGoal("describe the distribution of value", "clear_rising", "period", ["entity"],
             exercises="summarize_distribution / profile_dataset"),
    # -- harder questions, drawn from the agency hard tier -----------------------
    SeedGoal("are we getting slower at resolving customer issues?", "support_desk_slowing",
             "week", ["team"], exercises="multi-metric selection"),
    SeedGoal("which region has the weakest growth?", "regional_revenue_spread", "quarter",
             ["region"], exercises="ranking under a trend-flavoured question"),
    SeedGoal("do our enterprise and self-serve customers differ in engagement?",
             "plan_tier_separated", None, ["account"], exercises="grouping inference"),
    SeedGoal("is our customer complaint volume increasing?", "api_latency_rising", "day",
             ["service"], exercises="a question the data cannot answer"),
)


class SeedClient:
    """Thin API client. Tolerates a stack that restarts mid-seed."""

    def __init__(self, base_url: str, timeout: float = 120.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.token: str | None = None

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    def authenticate(self, email: str, password: str) -> None:
        """Register if the account is new, otherwise log in."""
        requests.post(
            f"{self.base_url}/v1/auth/register",
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        resp = requests.post(
            f"{self.base_url}/v1/auth/login",
            json={"email": email, "password": password},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        self.token = resp.json()["access_token"]

    def ensure_project(self, name: str) -> str:
        existing = requests.get(
            f"{self.base_url}/v1/projects", headers=self._headers(), timeout=self.timeout
        )
        existing.raise_for_status()
        for project in existing.json():
            if project.get("name") == name:
                return project["id"]
        created = requests.post(
            f"{self.base_url}/v1/projects",
            headers=self._headers(),
            json={"name": name, "description": "Seeded agent activity for the loop dashboard."},
            timeout=self.timeout,
        )
        created.raise_for_status()
        return created.json()["id"]

    def investigate(self, project_id: str, seed: SeedGoal) -> dict:
        resp = requests.post(
            f"{self.base_url}/v1/investigations",
            headers=self._headers(),
            json={
                "project_id": project_id,
                "goal": seed.goal,
                "dataset": {
                    "format": "csv",
                    "csv_text": seed.csv(),
                    "name": seed.fixture_id,
                    "time_field": seed.time_field,
                    "entity_id_fields": seed.entity_id_fields,
                },
            },
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()


def seed(
    client: SeedClient, project_id: str, *, duration_seconds: float, pace_seconds: float
) -> Counter:
    """Submit investigations round-robin through the catalogue until the duration elapses."""
    outcomes: Counter = Counter()
    started = time.monotonic()
    index = 0

    while time.monotonic() - started < duration_seconds:
        goal = GOAL_CATALOGUE[index % len(GOAL_CATALOGUE)]
        index += 1
        try:
            result = client.investigate(project_id, goal)
            outcomes[result.get("status", "unknown")] += 1
            elapsed = int(time.monotonic() - started)
            print(
                f"[{elapsed:5}s] {index:4} {goal.fixture_id:24} "
                f"{result.get('status', '?'):12} {goal.goal[:52]}",
                flush=True,
            )
        except requests.RequestException as exc:
            # A restarting stack should slow the seeder down, not end the run.
            outcomes["request_error"] += 1
            print(f"       ! {type(exc).__name__}: {str(exc)[:120]}", file=sys.stderr, flush=True)
            time.sleep(min(30.0, pace_seconds * 4))
            continue
        time.sleep(pace_seconds)

    return outcomes


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="scripts/seed-agent-activity.py",
        description="Populate the agent-loop Grafana dashboard with varied, free, offline activity.",
    )
    p.add_argument("--base-url", default=DEFAULT_BASE_URL)
    p.add_argument("--duration", type=float, default=1800.0,
                   help="Seconds to keep submitting (default 1800; timeseries panels need ~20min).")
    p.add_argument("--pace", type=float, default=4.0, help="Seconds between submissions.")
    p.add_argument("--email", default="seed@example.com")
    p.add_argument("--password", default="seed-password-123")
    p.add_argument("--project", default="Dashboard Seed")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    client = SeedClient(args.base_url)

    try:
        client.authenticate(args.email, args.password)
        project_id = client.ensure_project(args.project)
    except requests.RequestException as exc:
        print(f"could not reach {args.base_url}: {exc}", file=sys.stderr)
        print("Is the stack up? See 'Populating the dashboard' in docs/observability.md.",
              file=sys.stderr)
        return 1

    print(f"seeding project {project_id} for {args.duration:.0f}s "
          f"({len(GOAL_CATALOGUE)} goals, {args.pace:.1f}s pace)", flush=True)
    outcomes = seed(client, project_id, duration_seconds=args.duration, pace_seconds=args.pace)

    print("\nsubmitted:")
    for status, count in outcomes.most_common():
        print(f"  {count:4}  {status}")
    print("\nGrafana: http://127.0.0.1:3001 — EDGAR ▸ Agentic Investigation Loop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
