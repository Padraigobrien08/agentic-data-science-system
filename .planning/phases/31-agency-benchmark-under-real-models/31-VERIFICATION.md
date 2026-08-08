---
phase: 31-agency-benchmark-under-real-models
verified: 2026-08-07T11:30:00Z
status: passed
---

# Phase 31 Verification

## Goal

Take the measurement `suite_agency_v1` was built to take: point it at a real model, with
versioned prompts, repeated trials, and a published result.

## Verified Truths

1. The four policy decisions run on versioned, registry-managed prompts whose bodies are
   inspectable on disk and whose identity is exposed for the scoreboard.
2. `agentic/` imports nothing from `backend/`, and reaches `edgar_project`/`src` only from the
   two EDGAR bridge modules — enforced by an AST test that sees function-local imports.
3. `python3 -m agentic.evaluation` runs offline, free, and deterministic with no flags, no
   provider, and no prompt files present.
4. The suite runs against a model-backed policy over repeated trials under a spend ceiling,
   reporting per-property means, verdict stability, cost, and latency.
5. The harness refuses a model row when no provider is configured, or when the model is
   unpriced — either would publish a number that misrepresents what was measured.
6. Every `AgencyProperty` has a committed floor, asserted on every PR by the free offline suite.
7. No pull request can trigger a paid model run.
8. The README's remaining stated limits — MCP rate limiting and handshake auth, no CD, no
   backup/restore runbook, single-host Compose, agentic engine flag-gated — are unchanged.

## Result

`suite_agency_v1` is **saturated**: `gpt-5.4-mini` and the deterministic fixture policy both
score 100% on all nine properties across five trials, zero unstable cases, $0.26 total. The
suite separates broken agents from working ones but cannot rank competent ones. Published as
the headline finding rather than as a pass.

## Evidence

- `agentic/agent/policy.py` — `PolicyPrompts` injection seam with standalone defaults
- `backend/agents/prompts/agentic_*/{1.0.0,1.0.1}.md` — versioned prompt bodies
- `backend/agents/agentic_model_policy.py` — registry loading, never-raise degradation
- `agentic/evaluation/scoreboard.py` — pure multi-trial aggregation with stability tracking
- `backend/dev/agency_bench.py` — the harness, with provider and pricing guards
- `agentic/evaluation/baselines/fixture_floors.json` — committed regression floors
- `tests/agentic/test_domain_boundary.py` — AST boundary guard
- `tests/agentic/test_agency_floors.py` — the PR gate
- `docs/agent/agency-scoreboard.md` — the published measurement
- `.github/workflows/agency-bench.yml` — manual-only paid run
- `data/evaluation/agency/scoreboard-2026-08-07.json` — raw harness output

## Validation

- `python3 -m pytest -q` — 937 passed, 10 skipped
- `python3 -m ruff check .` — clean
- `python3 -m mypy backend` — 53 errors before and after; none in files this phase touched
- `python3 -m agentic.evaluation` — 13/13, offline
- `python3 -m backend.dev.agency_bench --policy fixture --trials 2 --format md` — renders
- `python3 scripts/export-openapi.py --check` — no drift

## Notes

Four guards in this phase were mutation-checked — a real violation introduced, the failure
confirmed, the violation removed: the domain boundary test, the budget-merge regression, the
floors gate, and the critic-sensitive case. Two of them were vacuous on first write and were
rewritten until they failed for the right reason.

## Carried Forward

- Hardening `AGENCY_CASES` so the suite can rank competent policies
- `ModelCall` persistence for agentic policy calls (from 31-01)
- `--max-cost-usd` truncation unproven against a real ceiling
- No cached-input pricing tier, so reported cost is a slight over-estimate
