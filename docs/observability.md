# Observability

The stack emits three signals. This page covers where they come from, how to run the
consumers, and what to look at first.

| Signal | Source | Consumer |
|---|---|---|
| Metrics | `prometheus_client` — `GET /metrics` (API) and `:9100` (worker) | Prometheus + Grafana |
| Traces | OpenTelemetry, OTLP/HTTP | Jaeger |
| Logs | `structlog`, JSON by default | container logs (no aggregator yet) |

## Running the stack

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
```

| UI | URL | First stop |
|---|---|---|
| Grafana | http://127.0.0.1:3001 | EDGAR ▸ **Agentic Investigation Loop** |
| Prometheus | http://127.0.0.1:9090 | Status ▸ Rules |
| Jaeger | http://127.0.0.1:16686 | service `edgar-backend`, span `agent.investigation` |

Everything is provisioned from files in [`ops/`](../ops) — datasources, the dashboard,
scrape config, and alert rules. There is no click-to-configure step, and UI edits to the
dashboard are overwritten on reload: change the JSON instead.

> **Local only.** All ports bind to `127.0.0.1` and Grafana runs with anonymous read
> access so the stack is useful immediately. Don't apply this overlay to a shared or
> public host without putting the UIs behind auth.

### How the API scrape authenticates

`GET /metrics` is behind `OpsTokenDep`, so Prometheus must present the ops bearer token.
Committing that token is not an option, so a one-shot `ops-token` service writes
`EDGAR_BACKEND_OPS_API_TOKEN` from your `.env` into a volume, and Prometheus reads it via
`credentials_file`. The token stays in `.env`; the committed config only names the path.

The worker's `:9100` endpoint is a plain `prometheus_client` server with no auth — it is
not routed through FastAPI.

## Populating the dashboard

A freshly started stack has no agent activity, so every panel is empty. Worse, a *little*
activity is misleading: seven of the thirteen panels are timeseries over `rate()` at a 15s
scrape, so a couple of runs render a technically correct picture that shows nothing.

`scripts/seed-agent-activity.py` supplies a varied workload.

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml up -d
python3 scripts/seed-agent-activity.py --duration 1800
```

Two settings are required and easy to miss:

- **`EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED=true` on both the api and the worker.** With it off,
  runs execute on the deterministic EDGAR chain and emit no `edgar_agent_*` metrics at all —
  which looks exactly like broken instrumentation.
- **`EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=true`**, unless you pass `--email` / `--password`
  for an account that already exists.

Give it around 20 minutes before judging the timeseries panels. Before concluding that data is
missing, check Prometheus **Status ▸ Targets** — a failed scrape is indistinguishable from
absent instrumentation on the dashboard itself.

### Free and offline

The seeder costs nothing. `build_agent_policy` falls back to the deterministic
`FixtureAgentPolicy` when no LLM provider is configured, and that policy still drives every
`edgar_agent_*` metric — components, experiments, hypothesis transitions, terminations.
Datasets are small in-memory CSVs rendered from the agency suite's fixtures, so nothing reaches
SEC either.

Two consequences worth expecting rather than debugging:

- **`edgar_agent_cost_usd_total` stays at zero.** The fixture policy has no token usage. This is
  the same "cost tracking is opt-in" behaviour described below, not a broken metric.
- **On a machine that *does* have a provider configured**, the backend uses the model policy and
  these runs cost money. That is your standing configuration, not something the script enables.

### What a healthy dashboard looks like

The workload spans intents on purpose, because the dashboard's most useful signals are the ones
that reveal a loop *not* working. After seeding, the three checks described below should visibly
pass:

| Check | Failing looks like | Should show |
|---|---|---|
| Is the loop iterating? | median iterations pinned at 1 | a spread above 1 |
| Is it adapting to the goal? | a flat single-tool profile | several tools, mix shifting with intent |
| Is it challenged by its own evidence? | only `→ supported` transitions | refuted and weakened transitions too |

The seed catalogue also includes goals whose data cannot support them, so the termination
breakdown shows more than `sufficient_evidence` and the per-tool failure panels are exercised.

## The agent loop dashboard

Reads top to bottom, from outcome to cause:

1. **Headline** — investigations, convergence rate, median iterations, estimated spend,
   and a breakdown of *why* runs stopped. Median iterations pinned at 1 means the loop
   is not actually iterating.
2. **Outcomes and duration** — terminal investigations by status over time, with p50/p95
   wall time.
3. **Components** — p95 decision latency per component and any component that raised.
   The four model-backed components (`goal_interpreter`, `hypothesis_generator`,
   `selector`, `critic`) track provider latency; the other six are deterministic.
4. **Experiments** — execution rate by tool with p95 duration, plus failure rate per tool.
   The tool mix should shift with goal intent; a flat single-tool profile means the loop
   is not adapting.
5. **Hypotheses and spend** — status transitions (evidence actually moving claims) and
   model calls with projected hourly cost. If nothing but `→ supported` ever appears, the
   loop is not being challenged by its own evidence.

### Metrics reference

| Metric | Labels | Notes |
|---|---|---|
| `edgar_agent_investigations_total` | `status`, `termination_reason` | terminal only; partial (resumable) calls excluded |
| `edgar_agent_investigation_duration_seconds` | `status` | histogram |
| `edgar_agent_investigation_iterations` | — | histogram |
| `edgar_agent_component_duration_seconds` | `component` | histogram, per loop component |
| `edgar_agent_component_errors_total` | `component`, `error_type` | a raising component terminates the run with `reason=error` |
| `edgar_agent_experiments_total` | `tool_name`, `status` | deterministic experiments |
| `edgar_agent_experiment_duration_seconds` | `tool_name` | histogram |
| `edgar_agent_hypothesis_transitions_total` | `from_status`, `to_status` | only real status changes |
| `edgar_agent_model_calls_total` | `component` | policy decisions |
| `edgar_agent_cost_usd_total` | `component` | `0` unless prices are configured — see below |
| `edgar_agent_terminations_total` | `reason` | typed termination reasons |

Every label comes from a closed enum or the experiment registry, so cardinality is bounded.

### Cost tracking is opt-in

`edgar_agent_cost_usd_total` and the loop's `max_cost_usd` budget both read
`EDGAR_BACKEND_LLM_MODEL_PRICES` (USD per **one million** tokens):

```bash
EDGAR_BACKEND_LLM_MODEL_PRICES='{"gpt-5.4-mini": {"input_per_1m": 0.15, "output_per_1m": 0.60}}'
```

Prices are operator config rather than a built-in table, because a stale hardcoded table
would silently produce wrong cost numbers. Unpriced models contribute `0.0`, so a spend
panel reading zero means *pricing is unconfigured*, not that inference was free.

## Traces

An investigation produces a span tree:

```
agentic.execute                     (run driver)
└── agent.investigation             goal, adapter, dataset, outcome, cost
    ├── agent.component.goal_interpreter
    ├── agent.component.hypothesis_generator
    ├── agent.iteration.0
    │   ├── agent.component.termination_policy
    │   ├── agent.component.planner
    │   ├── agent.component.selector
    │   ├── agent.component.executor
    │   ├── agent.component.evidence_updater
    │   ├── agent.component.hypothesis_updater
    │   └── agent.component.critic
    ├── agent.iteration.1
    └── agent.component.conclusion_synthesizer
```

The `agent.investigation` span carries the outcome as attributes (status, termination
reason, iteration/experiment/hypothesis/evidence counts, model calls, cost), so a single
trace answers "what did the agent do and why did it stop".

Component spans are recorded retroactively from their measured duration. That is
deliberate: the loop reports component *completion* rather than yielding a context
manager, which is what keeps `agentic/` free of any tracing dependency
(see [`domain-boundaries.md`](architecture/domain-boundaries.md)).

Traces reach Jaeger via `OTEL_EXPORTER_OTLP_ENDPOINT`. The exporter is constructed with an
explicit endpoint, so the value must include the full path
(`http://jaeger:4318/v1/traces`) — it is not appended automatically.

## Alerts

Twelve rules in [`ops/prometheus/rules/`](../ops/prometheus/rules), in three groups:

- **`agent-loop-health`** — failure rate, component errors, experiment failure rate,
  decision latency.
- **`agent-loop-quality`** — not outages, but signals that the agent is doing poor work:
  a sustained majority of `insufficient_evidence` conclusions, runs repeatedly hitting
  budget/safety ceilings instead of concluding, and spend rate.
- **`platform`** — worker loop liveness, queue backlog, stale leases, queue-observability
  integrity, API 5xx rate.

Thresholds are starting points for a single-host stack, not tuned SLOs.

Two conventions the tests enforce (`tests/test_observability_assets.py`):

- Every ratio alert clamps its denominator, so it stays silent with no traffic rather
  than evaluating to NaN.
- `WorkerLoopStalled` requires a non-zero last-tick timestamp, because the gauge is `0`
  until the worker's first tick and would otherwise fire on every cold start.

## Keeping the assets honest

A dashboard panel referencing a renamed metric fails silently — it just goes blank, and
an alert on a dead metric never fires. `tests/test_observability_assets.py` binds the
committed assets to the Prometheus registry:

- every `edgar_*` metric referenced by the dashboard or the alert rules must be
  registered in code;
- every `edgar_agent_*` family registered in code must appear in a dashboard or alert,
  so new metrics can't be emitted into the void;
- alert hygiene (severity, summary, `for` duration, clamped ratios) and the wiring
  between scrape config, datasource UIDs, and the dashboard.

Structural validation is left to the real tools:

```bash
docker run --rm -v "$PWD/ops/prometheus:/cfg:ro" --entrypoint promtool \
  prom/prometheus:v2.55.1 check rules /cfg/rules/agent_loop.rules.yml
```

```bash
docker compose -f docker-compose.yml -f docker-compose.observability.yml config --quiet
```

## Known gaps

- **No log aggregation.** Logs are structured JSON but go to container stdout; there is
  no Loki/ELK sink yet.
- **No SLOs or burn-rate alerts.** The rules are threshold alerts, not error budgets.
- **Dashboards cover the agent loop only.** HTTP, queue, and pipeline metrics are
  exposed and alerted on, but have no dedicated dashboard yet.
