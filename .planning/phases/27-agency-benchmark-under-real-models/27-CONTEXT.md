# Phase 27: Agency Benchmark Under Real Models - Context

**Gathered:** 2026-08-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Take the measurement the agency suite was built to take. `suite_agency_v1` scores whether the
investigation loop *reasons* well, and it was written to accept any `AgentPolicy` precisely so a
real model could be held to the same bar. That has never been run: `ModelAgentPolicy` has zero
non-test callers, and every published claim about adaptive reasoning currently describes
`FixtureAgentPolicy` — a keyword table.

This phase makes the model-backed policy a first-class, versioned, measurable surface: real
prompts under the existing prompt registry, a repeatable multi-trial benchmark harness, and a
committed scoreboard that replaces the README's "that measurement has not been run" caveat.

It does not change the loop, the components, the experiment registry, the scoring properties in
`agentic/evaluation/agency.py`, or the case set in `agentic/evaluation/cases.py`. Those are the
instrument; this phase points the instrument at something.

</domain>

<decisions>
## Implementation Decisions

### Domain purity
- **D-01:** The real boundary is two-tiered, verified by AST scan on 2026-08-07:
  - **`backend` — zero imports from anywhere under `agentic/`.** This is the hard invariant: the
    investigation domain knows nothing about persistence, settings, or the API. It holds after
    this phase and gains a test.
  - **`edgar_project` / `src` — six lazy imports, confined to two EDGAR bridge modules**
    (`agentic/adapters/edgar.py`, `agentic/experiments/tools/edgar_tools.py`), all inside
    functions. That is the adapter pattern working as designed: the domain-specific plug-in
    reaches into the domain-specific computation, and the generic path never pays for it. The
    test encodes this as an explicit allowlist rather than forbidding it outright.
- **D-02:** Model-backed benchmarking lives in `backend/dev/agency_bench.py`, following the
  existing `backend/dev/llm_context_compare.py` precedent. The `agentic/` runner stays offline.
- **D-03:** `python -m agentic.evaluation` with no flags stays offline, free, and deterministic.
  A contributor without an API key must still be able to run the suite.

### Prompt surface
- **D-04:** Prompts are injected into `ModelAgentPolicy`, never loaded by it. The four inline
  strings at `agentic/agent/policy.py:161-190` become constructor-supplied defaults so `agentic/`
  remains standalone; `backend/` overrides them with registry-loaded versioned bodies.
- **D-05:** The four policy roles join `AGENT_PROMPT_IDS` and get versioned files on disk, closing
  the asymmetry where the legacy EDGAR agents have a full registry and the agentic policy has
  one-liners.
- **D-06:** Policy calls persist `prompt_id` + `prompt_version` on `ModelCall` the same way the
  EDGAR agents do, so a scoreboard row is traceable to the exact prompt that produced it.

### Measurement validity
- **D-07:** A single pass is not a measurement. Model policies are non-deterministic even at
  `temperature=0`, so the harness runs N trials per case and reports variance. A case whose verdict
  is unstable across trials is itself a reportable finding.
- **D-08:** Cost and latency are captured through the existing observer (`InvestigationEnded`
  already carries `cost_usd`, `elapsed_seconds`, `model_calls`) rather than re-derived, so the
  scoreboard reports quality against spend.
- **D-09:** A model scoring **below** the fixture baseline is a legitimate published result, not a
  phase failure. The scoreboard reports what the suite measures.

### CI economics
- **D-10:** The fixture suite gates every PR — it is offline and free. The model suite is
  on-demand only and never runs per-PR.
- **D-11:** The per-property regression floor is committed to the repo and asserted by a test, so a
  prompt edit that degrades calibration fails the build without anyone remembering to look.

### the agent's Discretion
- Exact `PolicyPrompts` container shape, as long as defaults keep `agentic/` standalone
- Exact prompt body wording, as long as each carries its output schema, closed enum values, and
  explicit calibration framing
- Exact scoreboard table columns beyond the required quality/cost/latency/variance set
- Exact CLI flag names on the bench harness

</decisions>

<specifics>
## Specific Ideas

- The scoreboard is the phase's real deliverable. It reframes the project from "I built an agent"
  to "I built a way to measure whether agents reason well, and here is what it says" — a claim
  backed by code that already exists.
- Prompts must not push toward confidence. `agency.py` scores `calibrated_confidence` in both
  directions: the positive controls (`clear_rising_is_concluded`) fail a hedging prompt, and the
  negative controls (`flat_data_is_not_a_trend`, `noise_is_not_a_trend`,
  `two_points_are_not_a_trend`) fail an overclaiming one. The prompt has to thread that.
- `FixtureAgentPolicy` is a tuned rule engine on fixtures designed for it. It is a genuinely hard
  baseline, not a strawman, and should be presented as such in the scoreboard.
- Watch during 27-02: if every model scores near 100%, the cases are not discriminating and
  hardening `AGENCY_CASES` becomes a v1.6 item.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The instrument (do not change in this phase)
- `agentic/evaluation/agency.py` — the eight `AgencyProperty` values, `score_case`, and
  `AgencyReport.property_scores()`; the scoring contract this phase measures against
- `agentic/evaluation/cases.py` — `suite_agency_v1`, 12 cases, deliberately paired so that
  hedging and overclaiming both fail
- `agentic/evaluation/runner.py` — `run_case` / `run_agency_suite` / `format_report` / `main`
- `agentic/evaluation/fixtures.py` — deterministic fixture construction

### The policy seam
- `agentic/agent/policy.py` — `AgentPolicy` protocol, the four typed I/O models,
  `ModelAgentPolicy` and its four inline prompts (lines 161-190), `CostAwarePolicy`
- `agentic/agent/fixture_policy.py` — the deterministic baseline
- `backend/agents/agentic_model_policy.py` — `build_agent_policy`, `CostTrackingResponder`,
  `CostAwareModelPolicy`; the bridge between backend settings and the loop

### The prompt registry pattern to follow
- `backend/agents/prompt_registry.py` — `AGENT_PROMPT_IDS`, `load_registered_prompt`
- `backend/agents/prompt_loader.py` — front-matter format, `AgentPromptTemplate`, `source_uri`
- `backend/agents/prompts/critic/1.2.0.md` — a real versioned prompt body for reference

### Observation and budget (reuse, do not reinvent)
- `agentic/agent/observer.py` — `InvestigationEnded` already carries `cost_usd`,
  `elapsed_seconds`, `model_calls`; `AgentObserver` / `NULL_OBSERVER`
- `agentic/agent/budget.py` — `LoopBudget.max_cost_usd`, `BudgetTracker`
- `agentic/agent/loop.py` — `InvestigationLoop(policy=..., observer=...)` injection points

### Precedent for a backend-side dev harness
- `backend/dev/llm_context_compare.py` — the established shape for a backend-coupled
  developer tool that is not part of the product surface

### CI
- `.github/workflows/ci.yml` — the backend pytest job the fixture gate rides on

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `agentic/evaluation/` is complete and correct as a scoring instrument — this phase adds an
  aggregation layer over it and a caller, and changes none of its logic
- `run_agency_suite(policy=...)` already accepts an injected policy; `tests/agentic/test_agency_suite.py`
  already proves the injection works by scoring `HedgingPolicy` and `AlwaysTrendPolicy` below baseline
- `CostTrackingResponder` already accumulates real USD from provider token usage and satisfies
  `CostAwarePolicy`, so `LoopBudget.max_cost_usd` binds on live spend with no new work
- The observer already emits everything the scoreboard needs; no new event types are required
- `backend/agents/prompt_loader.py` already parses front matter and resolves versions

### Established Patterns
- Prompt bodies live on disk at `backend/agents/prompts/<role>/<version>.md` with
  `template_id` + `version` front matter; `prompt_id` is stable and never renamed once shipped
- Model-backed components persist `prompt_id` + `prompt_version` onto `ModelCall` rows
- `build_agent_policy` never raises on a missing provider — it degrades to `FixtureAgentPolicy`
  so the loop is always runnable offline. That contract must survive this phase.
- Boundary failures become typed safe terminations (`MalformedPolicyResponse` → `reason=error`),
  never crashes

### Integration Points
- `ModelAgentPolicy.__init__` gains an optional prompt container; all four `_call` sites read
  from it instead of inline literals
- `backend/agents/prompt_registry.py:AGENT_PROMPT_IDS` gains four entries
- `build_agent_policy` loads the four registered prompts and injects them
- `agentic/evaluation/runner.py` gains optional `observer` passthrough and trial support
- New `agentic/evaluation/scoreboard.py` aggregates many `AgencyReport`s (pure, no backend import)
- New `backend/dev/agency_bench.py` is the only place a model-backed suite run is assembled

### Known Risk
- The purity boundary is currently unenforced. Any convenience import from `agentic/` into
  `backend/` during this phase would quietly destroy the property that makes the domain reusable.
  27-02 adds the test that prevents it.
- A line-anchored grep (`^from backend`) is not sufficient to check this — the existing
  `edgar_project`/`src` imports are all *function-local* and invisible to it. The test must parse
  with `ast` and walk nested nodes, which is why 27-02 Task 1 specifies that explicitly.

</code_context>

<deferred>
## Deferred Ideas

- Hardening `AGENCY_CASES` if models saturate the suite — v1.6, informed by 27-02's results
- A second non-financial adapter to prove domain generalization — separate phase
- Publishing agency results per prompt *version* as a longitudinal series — needs more than one
  shipped prompt version to be meaningful
- OpenInference/Langfuse trace export — separate phase, unrelated to measurement validity

</deferred>

---

*Phase: 27-agency-benchmark-under-real-models*
*Context gathered: 2026-08-07*
