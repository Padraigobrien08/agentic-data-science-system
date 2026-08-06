# Agent Platform Roadmap

Backend-focused plan to close the gap between what this repo *is* (a well-engineered
analysis platform) and what it *claims to be* (a highly observable agent-orchestration
system for looped experimentation, exposed over MCP as an open-source API).

A companion frontend pass is deliberately out of scope here.

Status legend: `[ ]` todo · `[~]` in progress · `[x]` done
Effort: S (<1h) · M (half day) · L (multi-day)

_Created: 2026-08-06 from a backend capability review._

---

## Where the project actually stands

Genuinely strong, and not the problem:

- **Deterministic core** — `src/` numerical path with frozen regression tests; no numerics in prompts.
- **Persistence** — `AnalysisRun` / `RunStep` / `ToolCall` / `ModelCall` / `Artifact` /
  `RunExecutionJob` + investigation state, additive reversible Alembic.
- **Worker** — lease/heartbeat/stale reclaim/retry, verified against real Postgres.
- **Security** — JWT + ownership-404, auth rate limiting, security headers, closed-by-default CORS.
- **CI/supply chain** — ruff blocking, coverage floor 80%, pinned lockfiles, blocking pip-audit,
  CodeQL/Trivy/gitleaks, compose smoke.
- **Agentic domain model** — typed `InvestigationState`, hypotheses/evidence/experiments,
  deterministic ids, resume-from-checkpoint.

**The headline problem:** the infrastructure is production-grade; the three pillars the project
pitches itself on are the least-finished parts of it.

## The three gaps

### 1. "Highly observable" is currently false for the agent itself

`grep -rn "structlog|observe_|start_as_current_span" agentic/` returns **zero matches**. The
whole `agentic/` package — ten loop components, the policy, the experiment registry, the budget
tracker — emits no logs, no spans, no metrics. `backend/observability/metrics.py` has ~30 solid
Prometheus series for HTTP, worker queue and pipeline: observability is excellent for the
*plumbing* and absent for the *agent*.

Missing signals: iterations per investigation, termination-reason distribution, hypothesis
state transitions, experiment success/failure by tool, per-component decision latency, cost.

**Verified defect (2026-08-06):** three declared loop limits are dead code.
- `BudgetTracker.elapsed_seconds` is **never assigned** anywhere in `agentic/`, so
  `LoopBudget.max_elapsed_seconds` and `SafetyLimits.absolute_max_elapsed_seconds` can never fire.
- `agentic/agent/loop.py:170` calls `tracker.record_experiment(chosen.tool_name, failed=failed)`
  without `cost`, and `record_model_call()` takes no cost at all — so `cost_used_usd` is
  permanently `0.0` and `LoopBudget.max_cost_usd` can never fire.

An unbounded-wall-clock, unbounded-cost agent loop is a correctness problem, not just an
observability one. Fixing it shares plumbing with the latency metrics, so it belongs in A.

`O4` in `PRODUCTION-READINESS.md` is honest that metrics/traces have **no consumers** — no
dashboards, alert rules, or SLOs. For a project whose thesis is observability, shipping no
dashboard is the most visible possible miss.

### 2. The adaptive loop has never run the analysis the product is about

`docs/agent/backend-execution-wiring.md`: the EDGAR adapter with no `panel_csv` yields a
schema-only manifest and experiments "degrade gracefully"; EDGAR-through-the-engine over live
SEC data is an acknowledged follow-up. So `EDGAR_INTENT_TOOLS`
(`edgar_revenue_growth_analysis`, `edgar_margin_quality_analysis`,
`edgar_trend_break_analysis`, `edgar_peer_comparison`) exist but the loop only reaches them via
`in_memory` / `local_tabular` datasets. The flagship loop and the flagship dataset never meet.

"Show me the adaptive investigation on MSFT" is currently answered by a fixed chain, with the
interesting engine flag-gated off and fed synthetic frames.

### 3. MCP exposes EDGAR primitives, not the platform

`edgar_project/mcp/server.py` exposes 7 tools over **stdio only**. It can't be hosted (no
streamable-HTTP/SSE), and it exposes the *computation* but not the *product*: no
`start_investigation`, `get_investigation_state`, `list_hypotheses`, `get_evidence`, no artifact
fetch. No MCP resources (artifacts are a textbook fit), no auth. The platform is invisible over MCP.

---

## Workstream A — Agent observability (highest leverage)

Converts the project from "well-built" to "the observability one". Do this first: it is fastest,
directly serves the thesis, and makes B's payoff visible. B without A produces a working loop
nobody can see.

- [x] **A1. `AgentObserver` seam in the loop** — M _(landed 2026-08-06)_
  - `agentic/agent/observer.py`: no-op `AgentObserver` base + frozen event dataclasses +
    `LoopComponent` enum (bounded metric labels) + `RecordingObserver` for tests.
  - `InvestigationLoop` emits at run start/end (incl. partial + failed exits), iteration
    start/end, all ten components (incl. ones that raise), experiment execution, hypothesis
    transitions, model calls, and termination.
  - Components stay observation-free: the loop diffs hypothesis statuses and the budget tracker
    around each call, so all instrumentation lives in `loop.py`. `agentic/` still imports no
    structlog/OTel/prometheus.

- [x] **A2. Fix the dead budget/clock wiring** — M _(landed 2026-08-06)_
  - [x] Injected `Clock` (`agentic/agent/clock.py`, `ManualClock` for tests); `elapsed_seconds`
    refreshed at the top of each iteration, before the termination pre-check.
  - [x] Cost seam: optional `CostAwarePolicy.drain_cost_usd()` + `_invoke_policy` charging cost
    after each call whether or not it raised. `AgentPolicy` stays a four-method contract.
  - [x] Regression tests in `tests/agentic/test_investigation_observability.py` — verified to
    fail with the wiring reverted, so they genuinely cover the three previously-dead limits.
  - [x] Real token usage: `CostTrackingResponder` prices each completion from provider usage via
    `backend/llm/pricing.py`, and `CostAwareModelPolicy` exposes it to the loop. Prices are
    operator config (`EDGAR_BACKEND_LLM_MODEL_PRICES`, USD per 1M tokens) rather than a
    hardcoded table — a stale built-in table would silently produce wrong cost numbers, and
    unpriced models contribute `0.0` so budgets never bind on invented figures.

- [x] **A3. Backend observer implementation** — M _(landed 2026-08-06)_
  - `backend/observability/agent_observer.py:BackendAgentObserver` — OTel span tree
    `agent.investigation → agent.iteration.N → agent.component.{name}` nested under the existing
    `agentic.execute` span, structured logs bound to `analysis_run_id` (components at debug,
    the rest at info), and the `edgar_agent_*` metric families.
  - Metrics: `edgar_agent_investigations_total{status,termination_reason}`,
    `edgar_agent_investigation_iterations`, `edgar_agent_investigation_duration_seconds`,
    `edgar_agent_component_duration_seconds{component}`,
    `edgar_agent_component_errors_total{component,error_type}`,
    `edgar_agent_experiments_total{tool_name,status}`, `edgar_agent_experiment_duration_seconds`,
    `edgar_agent_hypothesis_transitions_total{from_status,to_status}`,
    `edgar_agent_model_calls_total{component}`, `edgar_agent_cost_usd_total{component}`,
    `edgar_agent_terminations_total{reason}`. All labels come from closed enums or the
    experiment registry, so cardinality is bounded. Prefix follows the existing `edgar_`
    convention rather than the bare `agent_` originally sketched here.
  - Every hook is wrapped so a tracing/metrics failure degrades observability instead of
    failing an investigation (covered by tests that inject a broken tracer and a broken metric).
  - Wired at the single injection point in `AgenticInvestigationExecutionService`.

- [x] **A4. Ship the consumers (closes O4)** — M _(landed 2026-08-06)_
  - `ops/grafana/dashboards/agent-loop.json` — 13 panels: outcomes, termination reasons,
    component latency/errors, experiment mix and failure rate, hypothesis transitions,
    model calls and spend. Provisioned via `ops/grafana/provisioning/` with fixed datasource
    UIDs; UI edits are overwritten, the JSON is the source of truth.
  - `ops/prometheus/rules/agent_loop.rules.yml` — 12 alerts in three groups. The
    `agent-loop-quality` group is the interesting one: it alerts on the agent doing *poor
    work* (sustained `insufficient_evidence`, runs hitting budget ceilings instead of
    concluding), not just on outages.
  - `docker-compose.observability.yml` — Prometheus + Grafana + Jaeger, all bound to
    loopback. An `ops-token` init service writes `EDGAR_BACKEND_OPS_API_TOKEN` to a volume
    that Prometheus reads via `credentials_file`, since `GET /metrics` is behind
    `OpsTokenDep` and the token must not be committed.
  - `docs/observability.md` — running it, the metrics reference, the span tree, and the
    known gaps (no log aggregation, no SLOs, no HTTP/queue dashboard).
  - `tests/test_observability_assets.py` — binds the committed assets to the Prometheus
    registry so a renamed metric breaks the build instead of silently blanking a panel.
    It caught one real gap on first run (`edgar_agent_experiment_duration_seconds` was
    emitted but never surfaced).
  - Verified against real tooling, not just syntax: `promtool check rules/config`, `docker
    compose config`, and a live bring-up confirming Prometheus loads 12 healthy rules,
    Grafana provisions the dashboard and both datasources, and all 16 dashboard queries
    execute against Prometheus.

**Workstream A is complete.** O4 in `PRODUCTION-READINESS.md` can be closed for the agent
loop and the platform metrics; log aggregation and SLOs remain open there.

## Workstream B — Close the loop over EDGAR

- [x] **B1. Materialize the EDGAR panel before the loop** — L _(landed 2026-08-06)_
  - `backend/services/edgar_panel_materializer.py` runs the existing deterministic pipeline
    (`build_panel_dataframe` → `compute_features_dataframe` → `write_features_csv`) into a
    run-scoped workspace and hands the resulting CSV to `EDGARAdapter` as `panel_csv`. No
    numerical logic moved: both engines compute identically.
  - The *features* frame is used rather than the raw panel, because it carries the identity
    columns plus `src.anomaly.FEATURE_COLS` — exactly what the adapter declares and the EDGAR
    experiment tools require.
  - `EDGAR_INTENT_TOOLS` are now reachable and lead the run. Verified end to end: a
    deterioration goal over a rising-revenue panel runs `edgar_trend_break_analysis` first,
    then three general tools, moves the hypothesis `proposed → active → rejected`, and
    terminates `insufficient_evidence` → `exhausted` → `partial_success`.
  - Failure is loud: `EdgarPanelUnavailable` marks the run `error` rather than degrading to a
    schema-only manifest, because an investigation over no data produces a confident-looking
    "insufficient evidence" conclusion indistinguishable from a real finding. Materialization
    moved after the `running` transition so the expensive network step is visible and its
    failures are attributed to the run.
  - The materializer is injectable, so the 15 new tests exercise the real execution path
    entirely offline.
- [ ] **B2. One real adaptive run, recorded** — M
  - goal → hypotheses → experiments → contradicting evidence → critic falsification →
    termination reason → evidence-linked conclusion. That trace is the README centerpiece.
- [x] **B3. Bounded parallel experiments per iteration** — M _(landed 2026-08-06)_
  - `LoopBudget.max_parallel_experiments` (default 1 — sequential runs take the original code
    path verbatim, no thread pool). The policy picks the lead experiment as before; remaining
    slots fill deterministically from the planner's ranked candidates, so `AgentPolicy` stays a
    four-method contract and model calls stay at one per iteration — a wider batch *lowers*
    cost per experiment.
  - Ordering guarantee: results fold in **selection** order, never completion order, so ids,
    evidence, and hypothesis updates remain a pure function of state. Proven by delaying a
    batch so it finishes reversed, and by a resume-determinism test with batching on.
  - Batch width is clamped by remaining budget, so it never overshoots `max_experiments` or a
    caller's `max_new_experiments` window. Shared artifact sink serialized via
    `LockedArtifactSink`; a raising tool propagates identically batched or not.
  - Also closed a gap from A2: the service ran on `LoopBudget()` defaults, so the elapsed-time
    and cost budgets were unreachable in a deployment. Budgets now come from settings
    (`EDGAR_BACKEND_AGENT_MAX_*`).
- [x] **B4. Investigation replay/diff** — L _(landed 2026-08-06)_
  - `agentic/agent/replay.py` + `diff.py` (pure domain) and
    `backend/services/investigation_replay_service.py`. See
    [`docs/agent/replay-and-diff.md`](../docs/agent/replay-and-diff.md).
  - Conclusion-first verdict (`identical` / `same_conclusion` / `diverged`) so reaching the
    same answer by a different route reads differently from reaching a different answer.
  - Replay is a fresh run seeded from the baseline id, so child ids align and hypotheses can
    be matched positionally; the candidate is relabelled afterwards. Replay deliberately takes
    no store — a checkpointing run would overwrite the baseline it is compared against.
  - Like-with-like is enforced: the service reconstructs the frame from the exact recorded
    panel and refuses (`ReplayDataUnavailable`) when it is gone, rather than re-fetching from
    the SEC and attributing a data change to the policy.
  - **Remaining:** no HTTP route (service-level only), and no batch "replay corpus" report.

## Workstream C — MCP as the platform surface

- [x] **C1. Orchestration MCP server** — L _(landed 2026-08-06)_
  - `backend/mcp/` — 9 tools (`start_investigation`, `get_investigation`, `get_conclusion`,
    `list_hypotheses`, `get_evidence`, `list_investigations`, `get_run_status`,
    `list_artifacts`, `get_artifact_preview`) and 2 resources (`artifact://{id}`,
    `investigation://{id}/conclusion`). See
    [`docs/mcp-platform-server.md`](../docs/mcp-platform-server.md).
  - **A client of the `/v1` API, not a second implementation.** Every tool is an HTTP call, so
    auth, owner scoping, validation, and 404-for-unauthorized are inherited rather than
    reimplemented — the MCP surface grants no access the token does not already have. Tested
    against the real app: a second user's token gets 404 on another's investigation.
  - Shares the EDGAR server's `ToolResponseEnvelope` contract; errors never cross the boundary
    as exceptions. List responses are capped so one call cannot flood an agent's context.
  - Found and fixed a real product bug while wiring artifact access: the loop emits chart specs
    as `application/vnd.chart+json`, which the preview endpoint rejected with 415 despite the
    bytes being plain JSON — those artifacts were unreadable through *every* surface, not just
    MCP. `artifact_previewable` now accepts any RFC 6839 `+json` structured-suffix type.
- [ ] **C2. Streamable-HTTP transport + bearer auth** — M
  - Reuse `backend/auth/tokens.py` so it can be hosted. Demo: point Claude Code at the endpoint
    and have it commission and inspect investigations.

## Workstream D — Open-source packaging (do last)

- [ ] **D1. Published OpenAPI spec artifact + versioned public API contract doc** — M
- [ ] **D2. "Add your own adapter / experiment tool" guide** — S
  - Promote the existing `docs/adapters/adapter-contract.md`.
- [ ] **D3. Prove input-agnosticism with one genuinely non-financial dataset in the eval suite** — M

## Cross-cutting — agency evaluation

- [ ] **X1. `suite_agency_v1`** — M
  - The eval framework (`edgar_project/evaluation/`) uses deterministic rubrics only, which is the
    right default and should stay. But for an *agentic* project the interesting question is agency
    quality: does the loop stop for the right reason, revise hypotheses against contradicting
    evidence, avoid redundant experiments?
  - Grow `tests/test_agentic_agency_evaluation.py` into a first-class suite with adversarial
    fixtures (flat data → must conclude insufficient; contradictory data → must weaken, not reject).
  - Measuring agency is a stronger differentiator than an LLM-judge rubric.

---

## Sequencing

**A → B → C → D**, with X1 folded in alongside B.

Rationale: A is the cheapest and most directly on-thesis; it also makes B demonstrable. C depends
on B being real (exposing an orchestration surface over a loop that can't run the flagship
dataset would be hollow). D is packaging and should follow substance.
