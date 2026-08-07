---
phase: 27-agency-benchmark-under-real-models
plan: 03
status: completed
completed: 2026-08-07
requirements:
  - AGCY-04
  - AGCY-05
---

# Summary 27-03: Scoreboard, README, and the CI gate

## What shipped

- **`agentic/evaluation/baselines/fixture_floors.json`** — per-property floors at the observed
  baseline with no margin, justified by a test asserting the fixture policy is deterministic.
- **`tests/agentic/test_agency_floors.py`** — the free PR gate. Five tests: determinism,
  per-property floors, pass-rate floor, floors-cover-every-property, every-floor-is-exercised,
  plus a regression that a never-challenging critic cannot score a perfect suite.
- **`docs/agent/agency-scoreboard.md`** — the published measurement.
- **`docs/agent/agency-evaluation.md`** — refreshed; its discrimination table and sample output
  still described a 10-case, 8-property suite.
- **`.github/workflows/agency-bench.yml`** — `workflow_dispatch` only, no `pull_request`/`push`.
- **`README.md`** — the stale "that measurement has not been run" bullet replaced with the
  actual finding; hardening added to In progress.
- **`data/evaluation/agency/scoreboard-2026-08-07.json`** — raw harness output archived so the
  published table is checkable.

## The measurement

| policy | trials | pass rate | all 9 properties | mean $ | p95 s |
|---|---|---|---|---|---|
| fixture | 5 | 100% | 100% | $0.0000 | 0.004 |
| gpt-5.4-mini | 5 | 100% | 100% | $0.0523 | 11.12 |

Zero unstable cases either row. Total spend $0.26. Prompts `1.0.1`, model resolved to
`gpt-5.4-mini-2026-03-17`, priced $0.75/$4.50 per 1M from the official docs.

**The suite is saturated.** It cannot distinguish a keyword-matching rule engine from a
frontier model. Published as the headline rather than as a 100% pass, because a perfect score
that separates nothing is a fact about the instrument.

## The prompt defect this run found

First live measurement: 62% (8/13), `terminates_for_the_right_reason` at 0% while the other
eight sat at 100%. That shape is a systematic fault, not a reasoning result, so it was traced
rather than published.

The 1.0.0 critic prompt said to decline with "`should_challenge: false` with nulls", but only
two of `CritiqueProposal`'s five fields are nullable. The model declined correctly, sent
`"message": null`, failed validation, raised `MalformedPolicyResponse`, and tripped the loop's
fail-safe into `reason=error` — losing every case that reached a supported claim. All four
prompts shared the trap (`rationale` is non-nullable everywhere).

Prompt `1.0.1` names the nullable fields: 13/13. One version, +38 points. `1.0.0` stays on disk
as the artifact that produced the 62%, which is the argument for versioning prompts rather than
inlining them.

## Deviations from plan

**The README says the opposite of what the plan assumed.** Plan 03 anticipated replacing the
caveat with a headline result and possibly promoting agency evaluation to Stable. The honest
outcome is "measured, and the suite does not discriminate", so the bullet states the saturation
as a current limit and agency stays out of Stable. The plan's own instruction covered this:
"If the suite turns out to be saturated ... say so plainly and record it as the signal to
harden `AGENCY_CASES`."

**`agency-evaluation.md` needed more than a link.** Its discrimination table claimed 10/10,
5/10, 8/10 against an 8-property suite. Refreshed with measured values (baseline 13/13,
`HedgingPolicy` 6/13, `AlwaysTrendPolicy` 11/13) and the new property documented.

**Prices had to be researched, not assumed.** The `0.15/0.60` figures in the settings docstring
are a placeholder and are 5×/7.5× below actual. Real rates taken from the official model page
and keyed to *both* the alias and the resolved snapshot, since `estimate_cost_usd` matches
exactly and the API bills the snapshot.

## Verification

- `937 passed, 10 skipped`
- `ruff check .` clean; `mypy backend` 53 before/after, none in new files
- `python3 -m agentic.evaluation` — offline, 13/13
- `scripts/export-openapi.py --check` — no drift
- Workflow YAML parses; `workflow_dispatch` is the only trigger; `ci.yml` does not reference
  the paid bench

## Still open

- **Hardening `AGENCY_CASES`** — now the highest-value work adjacent to this phase. The
  scoreboard is infrastructure until the suite can rank.
- **`--max-cost-usd` truncation is unproven against a real ceiling.** The run cost $0.26
  against a $2.00 ceiling, so the path is covered only by its unit test.
- **`ModelCall` persistence for agentic policy calls** (carried from 27-01) — product runs
  still produce no `ModelCall` rows for the four policy decisions.
- **No cached-input pricing tier**, so reported cost is a slight over-estimate.
