# Legacy Run Compatibility

The generalized investigation model is added **alongside** the existing EDGAR run
tables. No existing run, step, tool-call, model-call, artifact, or evaluation
record is modified or removed. This document describes how the two worlds relate.

## Origins

`investigations.origin` (`backend/models/enums_investigation.py`):

| Origin | Meaning | Source of truth |
|---|---|---|
| `native` | Created by the generalized investigation engine. | The investigation tables (normalized rows + latest checkpoint). |
| `legacy_import` | A representation of an existing EDGAR `analysis_runs` row. | The linked **`analysis_runs`** row. |
| `imported` | An investigation deserialized from an external source. | The imported state (checkpoint). |

## What becomes source of truth

- **Existing EDGAR runs stay authoritative.** For a `legacy_import`
  investigation, the numbers, artifacts, steps, and model calls continue to live
  in — and are read from — the original `analysis_runs` graph. The investigation
  row does not copy or replace them; it references the run via
  `investigations.analysis_run_id` (unique) and provides a generalized *view*
  (goal, datasets, a summary conclusion, status).
- **New investigations are authoritative for themselves.** A `native`
  investigation's source of truth is the investigation tables. It may *also*
  reference an `analysis_runs` row (e.g. a canonical child run that executed a
  deterministic experiment), but its reasoning state (hypotheses, evidence,
  decisions) lives in the new tables.

This keeps the deterministic EDGAR pipeline and its run history untouched while
letting the generalized model grow around it.

## How existing runs are surfaced

`SqlAlchemyInvestigationRepository.import_legacy_run(analysis_run)` builds a
domain `Investigation` (`origin = legacy_import`) from an existing run:

- **goal** — `InvestigationGoal(objective = run.orchestration_goal_text or
  input_payload.analysis_goal, adapter_id = "edgar",
  parameters = {tickers, analysis_run_id})`.
- **status** — mapped from `AnalysisRunStatus` to `InvestigationStatus`
  (`success/partial_success → converged`, `no_data → exhausted`,
  `error/cancelled → failed`, `running → running`, `pending/queued → created`).
- **datasets** — a single `DatasetReference` (`name = "EDGAR financial panel"`,
  `locator = run id`) when tickers are present.
- **conclusion** — a summary `Conclusion` from the run's
  `output_payload_json.message` / `final_summary`, dispositioned by status.
- **provenance** — `Provenance.system(note = "imported from analysis_run …")`.

The import is **idempotent**: `investigations.analysis_run_id` is unique, and
`import_legacy_run` returns the existing investigation if the run was already
imported (`test_import_legacy_run`). The original run row is verified untouched.

Because a legacy investigation is created through the same `create` path, it also
gets a checkpoint and a `created`/`imported` event, so it can be surfaced,
resumed, and reasoned over with the same repository API as native investigations —
while the run remains the numeric source of truth.

## Migration compatibility

- `014_investigation_persistence` is purely additive (`create_table` only). No
  column is added to or removed from existing tables; no data is migrated.
- Downgrade drops only the new tables; the full-chain Postgres test asserts
  `analysis_runs` (and the rest of the existing schema) survives a downgrade.
- Existing runs continue to work with zero changes; importing them into the
  generalized model is an explicit, opt-in, reversible operation (delete the
  investigation row to un-represent a run; the run is unaffected by the cascade
  because the FK is `ON DELETE SET NULL` from the investigation side).

## Non-goals

- No backfill job is run automatically; import is on demand.
- Legacy investigations do not re-derive EDGAR numbers into the new tables — they
  point at the run. Full generalized execution (hypotheses/experiments driven by
  the new engine) is reserved for `native` investigations produced when the
  investigation loop is wired into orchestration (a later phase).
