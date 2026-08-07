# Phase 30 Validation

## Commands

- `python3 -m pytest tests/test_seed_agent_activity.py -q --tb=short`
- `python3 -m pytest -q`
- `python3 -m ruff check .`
- `python3 -m agentic.evaluation`
- `docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d`

## Must Hold True

- The seeding workload runs with **no API key and no spend** — the fixture-policy fallback is
  asserted by test, not assumed.
- The workload reaches no external service; datasets are in-memory CSVs and no SEC call is made.
- Goals span at least five distinct intents, so the tool-mix panel is not degenerate.
- At least one seeded goal cannot be supported by its data, so terminations vary.
- Prometheus targets are verified healthy before any conclusion is drawn about missing data.
- The captured dashboard visibly passes its own three health checks: median iterations above 1,
  more than one tool in the mix, and hypothesis transitions beyond `→ supported`.
- `edgar_agent_cost_usd_total` reading zero is documented as expected for seeded runs, not
  presented as a working cost figure.
- The three existing screenshots and every unrelated README section are untouched.
- The core agency tier stays green and `python3 -m agentic.evaluation` exits 0.

## Blocked On

`30-CONTEXT.md` **Open Decision** — how a seeded dashboard is captioned in the README. 30-01 can
proceed without it; 30-02 cannot start until it is answered.

## Out of Scope

The dashboard JSON, the metric families, the observer, and every panel query. The
instrumentation is not the problem — its invisibility is. Also out of scope: a hosted demo, and
backlog items 2-7 from the standing goal.

## Mutation Checks Required

- The CSV-validity test: point a catalogue entry at a nonexistent fixture, confirm failure,
  restore.
- The offline guarantee test: it must fail if the fixture fallback is removed.
