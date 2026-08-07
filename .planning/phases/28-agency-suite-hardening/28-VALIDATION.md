# Phase 28 Validation

## Commands

- `python3 -m pytest tests/agentic -q --tb=short`
- `python3 -m pytest tests/test_agency_bench.py -q --tb=short`
- `python3 -m agentic.evaluation`
- `python3 -m backend.dev.agency_bench --policy fixture --trials 2 --tier all --format md`
- `python3 -m ruff check .`
- `python3 -m mypy backend`

## Must Hold True

- `suite_agency_v1` is frozen at its published 13 cases, stays independently runnable, and still
  scores 13/13 for `FixtureAgentPolicy` — the published scoreboard remains reproducible.
- Every case tagged `hard` fails `FixtureAgentPolicy`, enforced by a free offline test.
- Every hard case fails on a named `AgencyProperty`, not on a crash, a malformed request, or a
  tool capability gap.
- The hard tier's failures span more than one policy decision, so it cannot be cleared by
  improving a single method.
- The hard tier includes at least one case where declining is the correct behaviour, preserving
  the suite's pairing discipline.
- The PR gate fails both when the fixture policy regresses on core (floors) and when it starts
  passing hard cases (ceiling), and a ceiling breach names both possible causes.
- `python3 -m agentic.evaluation` runs offline, free, and deterministic with no provider.
- Every registered fixture is deterministic across repeated builds.
- Core-tier floors are unchanged by this phase.
- The scoreboard never averages core and hard into a single number.
- The README's remaining stated limits — MCP rate limiting and handshake auth, no CD, no
  backup/restore runbook, single-host Compose, agentic engine flag-gated — are unchanged.

## Mutation Checks Required

Two of the four guards written in phase 27 passed with the bug deliberately restored. Every new
gate here must be shown to fail for the right reason before it is trusted:

- Each hard case: construct a policy that makes the specific right judgement, confirm the case
  passes — so the case rewards the reasoning it claims to.
- The discrimination contract: add a hard-tagged case the fixture policy passes, confirm the
  contract test fails, remove it.
- The headroom ceiling: make a hard case trivially passable, confirm the ceiling test fails,
  revert.

## Out of Scope

The loop, the components, the experiment registry, the nine `AgencyProperty` definitions, and
`score_case`'s existing scoring blocks. Phase 27 showed these catch real defects; the gap being
closed is in the cases. A new `AgencyExpectations` field is permitted where no existing field
expresses a case's assertion, but it must score against an existing property rather than
introduce a new one.

## Carried From Phase 27 (not addressed here)

- `ModelCall` persistence for agentic policy calls
- Cached-input pricing tier — reported cost remains a slight over-estimate
- `--max-cost-usd` truncation still unproven against a real ceiling
