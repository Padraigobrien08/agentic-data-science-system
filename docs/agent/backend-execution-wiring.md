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
   - `{"adapter": "edgar", "panel_csv": "...", "entities": [...]}` — the EDGAR panel; with no
     `panel_csv` the manifest is schema-only (no frame) and experiments degrade gracefully.
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

## Scope / follow-ups

- Both call sites (sync route + worker) route through the same selector and service.
- EDGAR-*through-the-engine* over live SEC data (materializing the panel before the loop) and
  a richer artifact linkage from experiment results are deliberate follow-ups; this increment
  proves the full backend → loop → durable-persistence → status flow, verified offline.
- An investigation read-API/UI (hypotheses, evidence, decisions, timeline) consumes the
  persisted rows and the `output_payload_json` summary written here.

Tests: `tests/test_agentic_investigation_execution.py` (selection, end-to-end persistence,
status mapping, guards) — all offline and deterministic.
