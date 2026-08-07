---
phase: 27-agency-benchmark-under-real-models
plan: 02
status: completed
completed: 2026-08-07
requirements:
  - AGCY-03
---

# Summary 27-02: Model-backed suite execution

## What shipped

- **`tests/agentic/test_domain_boundary.py`** — AST scan over every `*.py` under `agentic/`,
  walking nested nodes so function-local imports are visible. Forbids `backend` outright;
  allowlists `edgar_project`/`src` to the two EDGAR bridge modules. Two guards keep the
  allowlist honest: one asserts both allowlisted files still exist (so a rename can't turn the
  rule into a silent no-op), one asserts they still use the allowance (so a dead exemption
  gets deleted rather than left as decoration).
- **Observer and budget passthrough** in `agentic/evaluation/runner.py` — `run_case` and
  `run_agency_suite` both accept `observer` and `budget`, forwarded to the loop. Loop kwargs are
  built conditionally so an omitted argument keeps the loop's own field default.
- **`agentic/evaluation/scoreboard.py`** — pure aggregation. `MetricsObserver` captures
  `InvestigationEnded`; `CaseStability` tracks per-case verdicts across trials; `PolicyScorecard`
  carries pass rate, per-property means, unstable cases, cost, and nearest-rank p95 latency;
  `Scoreboard.to_markdown()` renders a publishable table with explicit unstable-case and
  truncation sections.
- **`backend/dev/agency_bench.py`** — the CLI. Repeatable `--policy`, `--model`, `--trials`,
  `--max-cost-usd` (suite ceiling), `--budget-cost-usd` (per-run), `--out`, `--format`.

## Verification

- `924 passed, 10 skipped` (was 891 + 10 after 27-01; 33 new tests)
- `ruff check .` — clean
- `mypy backend` — 53 before, 53 after; none in `agency_bench.py`
- `python3 -m agentic.evaluation` — offline, no provider, 12/12
- `python3 -m backend.dev.agency_bench --policy fixture --trials 2 --format md` — renders the table
- End-to-end passthrough confirmed: 2 trials produced 24 `RunMetrics` (12 cases × 2), p95 3.8ms,
  $0.00, zero unstable cases

## Two bugs found and fixed during implementation

**1. A supplied budget silently disarmed the budget cases.** `run_case` had
`if effective_budget is None and case.max_experiments is not None` — so passing any budget
replaced the case's own `max_experiments` wholesale. The bench sets a per-run cost budget, which
would have made `budget_is_respected` pass vacuously in exactly the runs being published.
`max_experiments` from the case now merges onto the supplied budget via `model_copy`, so the
case's assertion wins and the caller's other fields survive.

**2. My first regression test for that bug was vacuous.** It asserted the shipped
`budget_is_respected` case ran within its cap — but `clear_rising` converges at two experiments
unaided, so capped and uncapped runs are indistinguishable. Reverting the fix left the test
green. Rewritten against a synthetic copy with `max_experiments=1`, below the natural stopping
point; the revert now fails it with a specific message.

Both the boundary test and the budget test were mutation-checked: a deliberate violation was
introduced, the test was confirmed to fail, and the violation removed.

## Deviations from plan

**`--policy model` fails loudly when no provider is configured.** Not in the plan.
`build_agent_policy` degrades to `FixtureAgentPolicy` on a missing provider — correct for the
product, wrong for a benchmark, where it would publish a deterministic rule engine's result
under a model's name and invalidate the scoreboard's central claim. The harness detects the
fallback and exits with a message naming the missing env var.

**`--budget-cost-usd` required adding `budget` passthrough to `run_agency_suite`.** The plan
assumed it was already there; only `run_case` accepted one.

## Notes for 27-03

- `p95_latency_seconds` is p95 across *investigations* (one per case), not across trials. Worth
  stating in the scoreboard doc so the number isn't misread.
- The fixture baseline currently scores 100% on all eight properties with zero unstable cases.
  Floors recorded in 27-03 Task 1 should be set just below that, and the saturation risk flagged
  in 27-CONTEXT is live: if models also score near 100%, the cases are not discriminating and
  hardening `AGENCY_CASES` becomes the v1.6 item.
- Confirm `--model` resolves before spending. `_agentic_model` defaults to `"gpt-5.4-mini"`; an
  unresolvable id fails every case as `reason=error`, which scores as a confident-looking zero.

## Next

27-03: committed per-property floors, the gate test, the benchmark run, the scoreboard document,
the on-demand workflow, and the README update. Task 2 needs a real paid run, which is why the
plan is marked `autonomous: false`.
