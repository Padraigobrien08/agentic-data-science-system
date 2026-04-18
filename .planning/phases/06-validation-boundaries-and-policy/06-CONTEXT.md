# Phase 6: Validation Boundaries and Policy - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Define how supported validation is identified, judged, and safely constrained before it expands into a broader product workflow. This phase covers validation-mode isolation policy, degradation taxonomy, live-use guardrails, and freshness semantics for `live` and `hybrid` evaluation.

It does not implement the remote object-store backend, summary-first trace UX, a first-class evaluation control plane, or child `AnalysisRun` linkage for live and hybrid execution; those belong to later v1.1 phases.

</domain>

<decisions>
## Implementation Decisions

### Validation isolation policy
- **D-01:** Validation runs must be explicitly separated from normal user work at the policy layer, with distinct mode identity and visibility rules instead of being treated as ordinary analyses with light labeling.
- **D-02:** Validation retention and namespace handling must stay evaluation-scoped rather than implicitly mixing benchmark and canary traffic into normal analysis histories, even if later phases link validation to child `AnalysisRun` rows.

### Degradation taxonomy
- **D-03:** Validation outcomes must distinguish at least `product_regression`, `upstream_sec_degraded`, `stale_source`, and `policy_skipped`.
- **D-04:** The degradation taxonomy must give operators enough context to decide whether follow-up belongs to upstream monitoring or product debugging.

### Live-use guardrails
- **D-05:** Fixture and `orchestration_mocked` evaluation remain the normal default validation paths.
- **D-06:** `live` and `hybrid` evaluation must be explicit operator-invoked workflows, non-merge-blocking by default, and not part of ordinary end-user run paths.

### Freshness semantics
- **D-07:** `live` and `hybrid` verdicts should judge invariants and freshness windows rather than exact output equality.
- **D-08:** Stale SEC data must degrade a validation result rather than being classified as a product regression.

### the agent's Discretion
- Exact schema and field names for validation mode, degradation classes, observation metadata, and policy flags
- Exact visibility or namespace mechanics, as long as validation remains clearly distinct from normal user work
- Exact freshness-window defaults and invariant checks, as long as live outputs are not treated as exact goldens
- Exact mapping of these policy decisions onto the existing `EvaluationRun` model and benchmark manifests, as long as later phases can implement supported workflows cleanly

</decisions>

<specifics>
## Specific Ideas

- User accepted the recommended defaults for all identified gray areas in one step:
  - validation should be explicitly separated from normal user work at the policy level
  - degradation should distinguish product regressions from SEC freshness or availability issues and policy-driven skips
  - fixture and mocked evaluation stay the normal default, while `live` and `hybrid` stay operator-invoked and non-merge-blocking by default
  - `live` and `hybrid` should be judged on invariants and freshness windows, not exact output equality

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project scope and acceptance criteria
- `.planning/PROJECT.md` — current milestone intent, brownfield constraints, and post-v1.0 trust posture
- `.planning/REQUIREMENTS.md` — `VALID-02` and `VALID-03` define the acceptance criteria for this phase
- `.planning/ROADMAP.md` — Phase 6 goal, dependencies, and success criteria
- `.planning/STATE.md` — current project position after v1.1 roadmap creation

### Milestone research and policy guidance
- `.planning/research/SUMMARY.md` — milestone synthesis, anti-features, and recommended phase order
- `.planning/research/FEATURES.md` — validation workflow table stakes, anti-features, and degradation expectations
- `.planning/research/PITFALLS.md` — SEC freshness, fair-access, and evaluation-isolation pitfalls this phase is meant to prevent

### Prior phase decisions that constrain this phase
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — raw payload access stays privileged and summary-first by default
- `.planning/phases/05-storage-and-ops/05-CONTEXT.md` — degraded-state reporting must remain explicit and operator-truthful

### Existing evaluation and run surfaces
- `edgar_project/evaluation/README.md` — current fixture-first evaluation scope and the documented `live`/`hybrid` gap
- `edgar_project/evaluation/schemas.py` — current `InputMode` contract and benchmark result shapes
- `edgar_project/evaluation/runner.py` — current skip behavior for `live` and `hybrid`
- `edgar_project/evaluation/benchmarks/suite_smoke.json` — existing scaffold case for `live` mode expectations
- `backend/models/evaluation_run.py` — persisted evaluation-run record that this phase’s policy should anchor to

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `edgar_project/evaluation/schemas.py` — already declares `fixture`, `live`, `hybrid`, and `orchestration_mocked` modes, so this phase can define policy without inventing a new evaluation vocabulary
- `backend/models/evaluation_run.py` — existing persisted evaluation-run record is the natural anchor for phase-level policy metadata and verdict summaries
- `backend/services/artifact_service.py` — already supports evaluation-scoped artifact keys via `evaluation_run_id`, which reinforces the decision to keep validation logically separate from ordinary runs
- `backend/api/routes/runs.py` — existing summary-first and admin-gated `include_payloads` behavior sets the precedent for keeping validation details bounded and privileged by default

### Established Patterns
- The evaluation stack is currently fixture-first: fixture and `orchestration_mocked` are implemented, while `live` and `hybrid` are declared but skipped with an explicit message
- The repo already treats degraded state as a meaningful operator signal in other surfaces, so validation taxonomy should follow the same explicitness instead of collapsing everything into pass/fail
- Secure-default API behavior already assumes raw payload access is privileged, which means this phase should avoid any policy that broadens live validation visibility by default

### Integration Points
- `edgar_project/evaluation/README.md`, `edgar_project/evaluation/runner.py`, and `edgar_project/evaluation/schemas.py` — mode semantics, current runner behavior, and benchmark expectations
- `edgar_project/evaluation/benchmarks/suite_smoke.json` — live-case scaffold that should align with the policy decisions from this phase
- `backend/models/evaluation_run.py` and `backend/models/enums.py` — persisted evaluation status and metadata seam
- `backend/auth/resource_access.py` and `backend/services/artifact_service.py` — existing evaluation artifact boundaries that later phases should preserve

</code_context>

<deferred>
## Deferred Ideas

- Dedicated validation dashboard or richer operator UI — belongs to Phase 9 `Evaluation Control Plane`
- Child `AnalysisRun` linkage and canonical live or hybrid execution plumbing — belongs to Phase 10 `Live/Hybrid Execution Hardening`
- Scheduled canary suites with alerting — deferred to later v1.x / v2 scope, not this policy phase

</deferred>

---

*Phase: 06-validation-boundaries-and-policy*
*Context gathered: 2026-04-18*
