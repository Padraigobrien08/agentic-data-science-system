# Phase 30: Observability, Demonstrated - Context

**Gathered:** 2026-08-07
**Status:** Ready for planning — blocked on one decision (see Open Decision)

<domain>
## Phase Boundary

Observability is this project's stated thesis, and it is invisible to anyone who does not clone
and run the stack. All three README screenshots are chat surfaces. The best-designed artifact in
the repository — the agent-loop Grafana dashboard, whose panels are explicitly built to answer
"is the loop actually adapting?" — has never been shown.

This phase makes it visible: a repeatable, offline, free workload that populates the dashboard
with varied agent activity, and a capture of the result in the README.

Out of scope: changing the dashboard, the metrics, the observer, or any panel query. The
instrumentation is good. It is undemonstrated.

</domain>

<decisions>
## Implementation Decisions

### The workload must be free and offline
- **D-01:** `build_agent_policy` degrades to `FixtureAgentPolicy` when no provider is configured,
  and the fixture policy still drives every `edgar_agent_*` metric — components, experiments,
  hypothesis transitions, terminations. Seeding therefore needs **no API key and costs nothing**.
- **D-02:** `POST /v1/investigations` accepts a user-supplied CSV over an `in_memory` adapter
  (`backend/services/investigation_create_service.py`). No SEC calls, no network, no rate limits.
  This is the seeding surface.
- **D-03:** `edgar_agent_cost_usd_total` will read zero throughout, because the fixture policy
  has no token usage. That is consistent with `docs/observability.md`'s existing "cost tracking
  is opt-in" note and must not be papered over in the caption.

### The workload must be varied, not just long
- **D-04:** The dashboard has 13 panels, 7 of them timeseries, with 16 targets using
  `rate()`/`increase()` at a 15s scrape. A handful of runs in one minute produces a technically
  correct and completely uninformative picture.
- **D-05:** Goals must span intents. A flat single-tool profile is precisely what
  `docs/observability.md` tells the operator means "the loop is not adapting" — a screenshot
  showing that would advertise the opposite of the claim. The agency suite's fixtures and goals
  are a ready-made varied workload and should be the source.
- **D-06:** Some runs should fail or terminate unusually. A dashboard where every run converges
  hides the panels that exist to surface trouble — `edgar_agent_component_errors_total`,
  the termination-reason breakdown, per-tool failure rate.

### the agent's Discretion
- Exact seeding script shape and where it lives (`scripts/` alongside `smoke-compose.sh` is the
  established precedent)
- How long the workload runs, as long as the timeseries panels are legible
- Whether one wide screenshot or several panel-group crops read better in the README

</decisions>

<specifics>
## Specific Ideas

The dashboard reads top to bottom from outcome to cause, and its own documentation names the
failure signatures each section exposes: "median iterations pinned at 1 means the loop is not
iterating"; "a flat single-tool profile means the loop is not adapting"; "if nothing but
`→ supported` ever appears, the loop is not being challenged by its own evidence". A good
screenshot is one where those three checks visibly *pass* — that is the actual claim being made,
and it is a stronger claim than "we have a dashboard".

`GET /metrics` is behind `OpsTokenDep` and Prometheus authenticates with a token written from
`.env` by the one-shot `ops-token` service. The seeder does not touch that path, but a failure
to scrape will look like a failure to instrument, so verify Prometheus targets are up before
concluding the workload is wrong.

The worker exposes its own metrics on `:9100` with no auth. Runs enqueued for background
execution are observed there rather than through the API process — worth knowing when a panel
looks empty.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### What is being demonstrated
- `ops/grafana/dashboards/agent-loop.json` — 13 panels; do not change
- `docs/observability.md` — the dashboard's reading order and the metrics reference
- `backend/observability/agent_observer.py` — `BackendAgentObserver`, the source of every metric
- `backend/observability/metrics.py` — the `edgar_agent_*` families

### The seeding surface
- `backend/api/routes/investigations.py` — `POST /v1/investigations`
- `backend/services/investigation_create_service.py` — CSV / records, `in_memory` adapter,
  sync vs enqueued execution
- `backend/agents/agentic_model_policy.py` — the offline fixture fallback that makes this free
- `agentic/evaluation/fixtures.py` and `agentic/evaluation/cases.py` — varied goals and datasets
  already written and known to exercise different intents

### Running the stack
- `docker-compose.yml`, `docker-compose.observability.yml`
- `ops/prometheus/prometheus.yml` — 15s scrape, `credentials_file` auth
- `scripts/smoke-compose.sh`, `scripts/stack` — established local-stack tooling
- `backend/config/settings.py` — `agentic_engine_enabled` must be on for the api **and** worker

### Where the result goes
- `README.md` — Product Screens
- `docs/screenshots/` — existing conventions

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- The agency suite is a varied, deterministic workload that already spans intents, entity
  counts, and both financial and non-financial column vocabularies.
- The offline fixture-policy fallback means the whole phase runs with no API key.
- `scripts/smoke-compose.sh` establishes the pattern for a script that drives a running stack.

### Established Patterns
- Scripts live in `scripts/` and are referenced from docs rather than assumed.
- `docs/observability.md` documents ports, auth, and the first thing to look at; new operator
  workflow belongs there rather than only in the README.

### Known Risk
- **A seeded screenshot is a claim.** Presented without qualification in a portfolio README it
  reads as production traffic. Presented honestly — a seeded local run, deterministic policy,
  zero spend — it is still a strong demonstration and an accurate one. Which framing to use is
  the user's call, not the implementer's.

</code_context>

<open_decision>
## Resolved Decision — 2026-08-07

**How a seeded dashboard is captioned: option A — explicit.**

The caption states that the data comes from a seeded local run using the deterministic policy,
with no model calls and zero spend. A caption that quietly implies production traffic would
undercut the "Known limits, stated plainly" register the rest of the README earns its
credibility from, and an honest one still demonstrates everything the dashboard is there to
demonstrate.

30-02 is unblocked.

</open_decision>

<deferred>
## Deferred Ideas

- A hosted demo with a live dashboard
- Screenshotting Jaeger traces as well as Grafana
- Backlog items 2-7 from the standing goal

</deferred>

---

*Phase: 30-observability-demonstrated*
*Context gathered: 2026-08-07*
