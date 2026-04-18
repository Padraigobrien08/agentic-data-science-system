# Phase 9: Evaluation Control Plane - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Promote supported evaluation workflows into first-class persisted product records so operators can start, list, reopen, and review evaluation runs and their case outcomes without relying on ad hoc CLI/file output.

This phase covers the operator entry surface, suite identity contract, ownership scope, and persisted review shape for evaluation runs and case results. It does not implement child `AnalysisRun` linkage for live or hybrid execution, broaden live validation into default user paths, or replace app-owned artifact delivery with storage-native access.

</domain>

<decisions>
## Implementation Decisions

### Operator entry surface
- **D-01:** The supported evaluation control plane should be API-backed first, with the CLI kept as a compatibility path rather than remaining the primary product workflow.
- **D-02:** Phase 9 should treat persisted evaluation runs as product resources that other surfaces can call, not as side effects of local-only scripts.

### Supported suite contract
- **D-03:** Supported evaluation launches should use curated suite IDs or approved manifests, not arbitrary repo file paths supplied at runtime.
- **D-04:** The control plane should make suite identity explicit and auditable so a later operator can tell exactly which supported evaluation definition was run.

### Evaluation ownership scope
- **D-05:** Supported evaluation runs should be project-scoped by default.
- **D-06:** Evaluation ownership and visibility should follow the existing project-owner boundary instead of introducing a new global operator-only auth model in this phase.

### Case review shape
- **D-07:** Operators should reopen an evaluation run into a persisted run summary plus explicit per-case results, not just one opaque `results_json` blob.
- **D-08:** Case-level outcomes should remain reviewable as first-class persisted records even if summary JSON views still exist for export or convenience.

### the agent's Discretion
- Exact service and API route shape for evaluation-run create/list/detail operations
- Exact persistence model for case results, as long as they are first-class persisted records rather than only an opaque blob
- Exact CLI compatibility path, as long as CLI usage no longer defines the only supported workflow
- Exact operator review surface, as long as evaluation history is project-scoped, auditable, and reopenable

</decisions>

<specifics>
## Specific Ideas

- User accepted all recommended defaults in one step:
  - API-backed control plane first, CLI retained only as a compatibility path
  - curated suite identity instead of arbitrary path-based suite selection
  - project-scoped evaluation ownership by default
  - persisted run summary plus explicit per-case results rather than a single opaque `results_json` blob
- The existing CLI and benchmark files remain useful developer tooling, but they should stop being the only supported operator workflow.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — current milestone intent, validated trust boundaries, and the remaining v1.1 scope after Phase 8
- `.planning/ROADMAP.md` — Phase 9 goal, dependency on Phase 8, and the three success criteria for supported evaluation workflows
- `.planning/REQUIREMENTS.md` — `VALID-01` and `EVAL-01` define the acceptance criteria for this phase
- `.planning/STATE.md` — current project position and continuity after Phase 8 completion

### Prior decisions that constrain this phase
- `.planning/phases/06-validation-boundaries-and-policy/06-CONTEXT.md` — validation stays policy-distinct from normal user work; live and hybrid remain explicit operator-invoked workflows
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — raw payload access stays privileged and summary-first by default
- `.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md` — artifact identity and app-owned authorization boundaries remain stable
- `.planning/phases/08-summary-first-large-trace-views/08-CONTEXT.md` — operator drill-down surfaces should stay bounded, typed, and summary-first

### Existing evaluation workflow surfaces
- `edgar_project/evaluation/README.md` — current fixture-first benchmark model, live/hybrid guardrails, and CLI usage expectations
- `edgar_project/evaluation/schemas.py` — current benchmark, result, policy, and summary contracts
- `edgar_project/evaluation/runner.py` — current execution path, skip behavior for live/hybrid, and current JSON/file-output assumptions
- `edgar_project/evaluation/summary_report.py` — current suite summary shape and failure-brief model
- `edgar_project/cli.py` — current `evaluate` CLI entrypoint and path-based suite invocation contract

### Existing persistence and ownership seams
- `backend/models/evaluation_run.py` — existing persisted evaluation-run aggregate and current coarse `summary_json` / `results_json` fields
- `backend/schemas/evaluation_run.py` — existing wire models for evaluation runs
- `backend/models/project.py` — project-level relationship for evaluation runs
- `backend/auth/resource_access.py` — owner-scoped access logic already understands `evaluation_run_id` on artifacts
- `backend/services/artifact_service.py` — evaluation-scoped artifact ingestion and storage paths
- `backend/api/router.py` — confirms no evaluation routes exist yet, so Phase 9 is defining a new product surface

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/models/evaluation_run.py` and `backend/schemas/evaluation_run.py` — already provide a persisted evaluation-run record and basic create/read/update schema surface
- `edgar_project/evaluation/schemas.py` — already provides typed case/result/policy structures, including `ValidationObservation` and degradation classes
- `edgar_project/evaluation/summary_report.py` — already provides compact summary and failure-brief formatting logic that can inform persisted overview views
- `backend/auth/resource_access.py` and `backend/services/artifact_service.py` — already support owner-scoped access to evaluation artifacts and evaluation-specific artifact storage roots

### Established Patterns
- The current supported workflow is CLI-first and file-output-first: `edgar_project.cli evaluate` runs a suite and writes `*_results.json` / `*_summary.json` to disk
- Evaluation persistence exists only as a coarse aggregate row today; there is no first-class case-result resource or API route
- Project ownership is the established auth boundary across runs and artifacts, and evaluation artifacts already follow that model
- Live and hybrid evaluation are already policy-gated and non-default, so Phase 9 should promote supported workflows without weakening those boundaries

### Integration Points
- New evaluation API routes will need to mount under the authenticated FastAPI surface in `backend/api/router.py`
- New service and repository code should center on `EvaluationRun` and a persisted case-result model or equivalent first-class persistence seam
- CLI compatibility should delegate toward the same supported evaluation persistence flow rather than maintaining a separate truth source
- Any future frontend/operator surface should follow the existing server-side API bridge pattern in `frontend/src/lib/api/*`, but Phase 9 should not depend on inventing a new auth model

</code_context>

<deferred>
## Deferred Ideas

- Child `AnalysisRun` linkage for live and hybrid validation cases — belongs to Phase 10 `Live/Hybrid Execution Hardening`
- Global cross-project operator console for evaluations — out of scope for this phase; Phase 9 stays project-scoped by default
- Arbitrary file-path suite execution as a supported product surface — keep as developer tooling only, not the control-plane contract

</deferred>

---

*Phase: 09-evaluation-control-plane*
*Context gathered: 2026-04-18*
