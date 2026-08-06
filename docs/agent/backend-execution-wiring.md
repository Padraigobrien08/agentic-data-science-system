# Backend Execution Wiring (flag-gated)

The adaptive investigation loop (`agentic/agent`) is wired into the existing backend run
path **additively and behind a feature flag**, so the deterministic EDGAR pipeline stays
the default and is never disturbed. Enabling the engine is a two-part decision: an operator
turns the flag on, *and* a specific run opts in. Nothing changes unless both are true.

## The flag

`EDGAR_BACKEND_AGENTIC_ENGINE_ENABLED` (`Settings.agentic_engine_enabled`, default `false`).

- `false` → every run uses `EdgarPipelineExecutionService` (unchanged behavior).
- `true` → a run may select the agentic engine via `input_payload_json.engine == "agentic"`.
  Runs that don't opt in still use the EDGAR path.

Enable it on **both** the `api` process (synchronous `/execute`) and the `worker` process
(queued runs) if you use the background queue.

## Engine selection

`select_run_engine(run, settings)` in
`backend/services/agentic_investigation_execution_service.py` is the single decision point,
used by both the synchronous route (`POST /v1/runs/{id}/execute`) and the worker loop
(`backend/worker/loop.py`). It returns `"edgar"` unless the flag is on **and** the run opts
in — a deliberately conservative default.

## What the agentic path does

`AgenticInvestigationExecutionService.execute_analysis_run(...)` mirrors the EDGAR service's
lifecycle contract (executable-status guards, `queued` requirement from the worker,
cancellation via `RunCancelledDuringExecution`, terminal-status commit) and then:

1. **Resolves a dataset** from `input_payload_json.dataset` into a typed `DatasetManifest`
   plus a live frame, via an input adapter:
   - `{"adapter": "in_memory", "records": [...]}` — inline records (offline).
   - `{"adapter": "local_tabular", "path": "/abs/file.csv"}` — a CSV/Parquet file.
   - `{"adapter": "edgar", "entities": [...]}` — the EDGAR panel, **materialized from SEC
     data** into the run's workspace (see below). Pass `panel_csv` to point at an existing
     file or fixture instead, and `refresh: true` to bypass the local SEC cache.
   Optional `time_field` / `entity_id_fields` hints are structural, not domain vocabulary.
2. **Runs `InvestigationLoop`**, checkpointing every iteration into the durable investigation
   persistence layer through `SqlAlchemyInvestigationStore` (linked to the run's project,
   user, and `analysis_run_id`; the investigation `domain_id` is seeded to the run id).
3. **Maps the terminal `InvestigationStatus`** onto `AnalysisRunStatus`
   (`converged → success`, `exhausted → partial_success`, `failed → error`) and writes a
   compact `output_payload_json` summary (conclusion, termination reason, hypotheses,
   counts, dataset identity) for the read-API / UI.

## Decision policy (LLM vs deterministic)

`backend/agents/agentic_model_policy.py:build_agent_policy(settings)` returns:

- `ModelAgentPolicy` backed by the configured `ChatCompletionProvider` when
  `EDGAR_BACKEND_LLM_PROVIDER=openai` (JSON responses, temperature 0), or
- `FixtureAgentPolicy` (deterministic) when no LLM is configured.

The loop is therefore **offline-safe**: with no model it still interprets the goal, selects
experiments, updates hypotheses, and terminates for a typed reason — it just makes
deterministic decisions. Deterministic *computation* never goes through the policy.

## Example opt-in payload

```json
{
  "engine": "agentic",
  "analysis_goal": "revenue is increasing over time",
  "dataset": {
    "adapter": "in_memory",
    "name": "rev",
    "records": [{"entity": "A", "period": "2021-0", "revenue": 5}],
    "time_field": "period",
    "entity_id_fields": ["entity"]
  }
}
```

## EDGAR panel materialization

An EDGAR-adapter run used to reach the loop as a *schema-only* manifest — columns
declared, `frame=None` — so every EDGAR experiment degraded and the adaptive loop could
never actually analyze SEC data. `backend/services/edgar_panel_materializer.py` closes that:

1. A run-scoped `RunWorkspace` is built under `EDGAR_BACKEND_RUN_WORKSPACE_ROOT`, keyed by
   the analysis-run id — the same isolation the EDGAR pipeline path uses, so two runs never
   share a panel.
2. The existing deterministic pipeline runs into it: `build_panel_dataframe` →
   `compute_features_dataframe` → `write_features_csv`. **No numerical logic lives in the
   materializer**; acquisition and computation stay in `src`/the MCP adapters, so both
   engines compute identically.
3. The resulting `features.csv` is handed to `EDGARAdapter` as `panel_csv`, which profiles
   it into a manifest with a real frame. The *features* frame is used rather than the raw
   panel because it carries the identity columns plus `src.anomaly.FEATURE_COLS` — exactly
   the schema the adapter declares and the EDGAR experiment tools require.
4. The workspace and panel provenance (row count, tickers, CSV path) are recorded in
   `meta_json` under `run_workspace` and `edgar_panel`.

With a frame present, `EDGAR_INTENT_TOOLS` become reachable and are prepended to the intent
candidates, so an EDGAR run leads with a domain tool
(`edgar_trend_break_analysis`, `edgar_peer_comparison`, …) before falling back to the
general layer.

**Failure is loud.** If the panel cannot be materialized (no tickers, no extractable
metrics, or an upstream SEC/IO failure) the service raises `EdgarPanelUnavailable` and marks
the run `error`. It deliberately does *not* fall back to a schema-only manifest: an
investigation over no data reaches a confident-looking "insufficient evidence" conclusion
that is indistinguishable from a real analytical finding. Because materialization is the
expensive network step, it runs *after* the run is marked `running`, so the work is visible
and its failures are attributed to the run rather than escaping unhandled.

The materializer is injectable (`panel_materializer=`), which is how the test suite stays
fully offline while exercising the real execution path.

## Observability and cost

The run driver injects `BackendAgentObserver`
(`backend/observability/agent_observer.py`) into the loop, turning the loop's typed
events (see [investigation-loop.md](investigation-loop.md#observability)) into the three
signals the platform already speaks:

- **Traces** — `agent.investigation → agent.iteration.N → agent.component.{name}`,
  nested under the existing `agentic.execute` span, so one investigation reads as a
  flame graph of the agent deciding. Component spans are created retroactively from
  their measured duration, which keeps `agentic/` free of any tracing dependency.
- **Logs** — structured events bound to `analysis_run_id`; component-level events log
  at debug (there are ten per iteration), everything else at info.
- **Metrics** — the `edgar_agent_*` families: investigations by status and termination
  reason, iterations, component latency and errors, experiments by tool and status,
  hypothesis transitions, model calls, and cost. Every label comes from a closed enum
  or the experiment registry, so cardinality stays bounded.

Every hook is wrapped so a tracing or metrics failure degrades observability rather than
failing the investigation.

**Cost.** `build_agent_policy` returns a `CostAwareModelPolicy` wrapping a
`CostTrackingResponder`, which prices each completion's real token usage via
`EDGAR_BACKEND_LLM_MODEL_PRICES` (USD per one million tokens). The loop drains that cost
after every policy decision, so `LoopBudget.max_cost_usd` binds on actual spend. Models
with no configured price contribute `0.0` — the budget never binds on invented numbers.

## Scope / follow-ups

- Both call sites (sync route + worker) route through the same selector and service.
- EDGAR-*through-the-engine* over live SEC data (materializing the panel before the loop) and
  a richer artifact linkage from experiment results are deliberate follow-ups; this increment
  proves the full backend → loop → durable-persistence → status flow, verified offline.
- An investigation read-API/UI (hypotheses, evidence, decisions, timeline) consumes the
  persisted rows and the `output_payload_json` summary written here.

Tests: `tests/test_agentic_investigation_execution.py` (selection, end-to-end persistence,
status mapping, guards) — all offline and deterministic.
