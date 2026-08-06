# Investigation Replay & Diff

Replay answers a question that is otherwise very hard to answer about an agent: **we changed
the model / the prompt / the budget — did the analysis actually change, or only the route to
it?**

An investigation persists everything needed to re-pose its question (goal, dataset manifest,
and a deterministic id scheme seeded per investigation). Replay re-runs that question under
different conditions and diffs the outcome.

## The verdict

The comparison is deliberately **conclusion-first**. Reaching the same answer by a different
route is a much weaker signal than reaching a different answer, so the top-level verdict
separates them rather than reporting an undifferentiated list of deltas:

| Verdict | Meaning |
|---|---|
| `identical` | Same conclusion, same termination reason, same experiments in the same order. |
| `same_conclusion` | The answer and termination match; the route differed (different experiments, order, or hypothesis outcomes). |
| `diverged` | The conclusion, its disposition, or the termination reason changed. |

`InvestigationDiff.summary()` renders one line suitable for a log, CLI, or PR comment:

```
identical: same conclusion, termination, and experiment sequence
same conclusion via a different route (different experiments)
diverged: disposition supported → insufficient_evidence; termination sufficient_evidence → budget_exhausted
```

## Domain API

`agentic/agent/replay.py` and `agentic/agent/diff.py` are pure domain code — no persistence,
no infrastructure, no model access.

```python
from agentic.agent import replay_investigation

result = replay_investigation(baseline, frame=frame, policy=new_policy)
print(result.summary())          # one-line verdict
result.diff.changed_hypotheses   # which claims landed differently
result.diff.model_dump(mode="json")   # serializable for transport/storage
```

Key properties:

- **A replay is a fresh run, not a resume.** It starts from empty state so every decision is
  made again under the new conditions.
- **Ids are seeded from the baseline**, which is what lines the two runs' hypotheses and
  experiments up for comparison (`{seed}-hyp-{index}`). Hypotheses are matched by id, so a
  policy that proposes a *different statement* at the same position is surfaced rather than
  silently treated as an unrelated hypothesis.
- **The candidate is relabelled** (`{baseline_id}::replay`) once the run finishes, so it is a
  distinct investigation even though its child ids align.
- **Replay never takes an `InvestigationStore`.** Sharing the baseline's seed means a
  checkpointing run would overwrite the very investigation being compared against. Persisting
  the candidate is the caller's decision, after relabelling.
- **Frames are not persisted**, so the caller supplies the data. Replaying against different
  data is legitimate (does the conclusion hold on a later period?) but must be an explicit
  choice: pass `same_dataset=False`, and `ReplayResult` records it so a divergence is not
  misattributed to the policy.

## Backend API

`backend/services/investigation_replay_service.py` replays the investigation attached to a
persisted analysis run:

```python
result = InvestigationReplayService(session).replay_run(
    analysis_run_id,
    policy=build_agent_policy(settings),   # defaults to the configured one
    budget=LoopBudget(max_experiments=3),  # optional: is a cheaper run as good?
)
```

**Like-with-like is the defining constraint.** The service reconstructs the frame from the
*exact panel the baseline analyzed*, recorded on the run as `meta_json.edgar_panel`. It never
re-fetches from the SEC. When that file is gone it raises `ReplayDataUnavailable` rather than
re-materializing: a diff computed against different data would attribute to the policy a
change that may have come from the data.

Reconstruction order:

1. `meta_json.edgar_panel.features_csv` — the recorded panel (preferred).
2. `input_payload_json.dataset.records` — inline records.
3. `input_payload_json.dataset.path` / `panel_csv` — a referenced file.

Anything else is refused.

The replay emits its own traces and metrics through `BackendAgentObserver`, because the
candidate is a real investigation run whose cost and latency are worth seeing.

## What this is for

- **Model upgrades** — replay a corpus of runs under a new model; count how many `diverged`.
- **Prompt changes** — same, for the policy prompts.
- **Budget tuning** — does `max_experiments=3` reach the same conclusions as `8`?
- **Regression evidence** — a diff is serializable, so a replay corpus can gate a change.

## Follow-ups

- No HTTP route yet; replay is service-level. A `POST /v1/investigations/{id}/replay`
  returning the serialized diff is the natural next step.
- Batch replay across many runs (a "replay corpus" report) is not implemented; the service
  is per-run today.
