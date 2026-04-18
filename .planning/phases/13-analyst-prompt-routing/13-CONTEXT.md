# Phase 13: Analyst Prompt Routing - Context

**Gathered:** 2026-04-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Make normal analyst phrasing in workspace chat map to the currently supported deterioration, anomaly, and peer-comparison workflows, and replace dead-end unsupported-intent failures with actionable rewrite guidance.

This phase covers deterministic routing expansion, prompt-scoped ticker narrowing, unsupported guidance, and the policy boundary for any optional LLM rescue path.

It does not redesign the chat answer surface, inline evidence navigation, or the standalone run page. It also does not broaden the analytical capability set beyond the existing supported deterioration/trend, anomaly, and peer-comparison flows.

</domain>

<decisions>
## Implementation Decisions

### Thesis-style single-company routing
- **D-01:** Broad analyst asks like “is margin pressure temporary or structural?” or “is cash flow quality slipping?” should route to the closest supported deterioration or trend path when the prompt contains enough business cues.
- **D-02:** Phase 13 should broaden support for normal analyst language rather than requiring explicit anomaly or deterioration keywords in every successful prompt.

### Peer and comparison language boundary
- **D-03:** Peer routing should accept broader relative-language cues such as `vs`, `versus`, `relative to`, `weaker`, `stronger`, and `underperform`.
- **D-04:** Multiple tickers alone must not force peer mode; peer routing still needs explicit relative/comparison language.

### Prompt-named scope handling
- **D-05:** If the prompt names a subset of companies already in the workspace, the run should narrow to that subset instead of silently using the whole workspace scope.
- **D-06:** If the prompt names symbols outside the workspace scope, the product should stop and return guidance instead of silently expanding scope.

### Unsupported guidance contract
- **D-07:** When routing still fails, the product should return 2-3 concrete rewrite suggestions shaped around the current prompt and workspace scope.
- **D-08:** Unsupported handling should become a usable next-step surface, not just a technical unsupported-intent error.

### LLM rescue boundary
- **D-09:** Routing remains deterministic-first by default.
- **D-10:** Any model-assisted rescue path must be explicit, config-gated, and auditable when it is used after deterministic routing fails.

### the agent's Discretion
- Exact deterministic cue expansion in `intent.py` and its relationship to the richer preference parsing already in `goal_preferences.py`
- Exact shape of prompt-to-workspace ticker narrowing and how the UI/backend communicate out-of-scope symbols
- Exact rewrite-guidance format and where it is surfaced, as long as the user gets concrete next phrasing rather than a dead end
- Exact gating and audit semantics for any optional LLM rescue path, as long as deterministic routing remains the default trust boundary

</decisions>

<specifics>
## Specific Ideas

- User selected all five identified gray areas and chose the recommended direction on each:
  - `1A` broaden thesis-style single-company routing to the closest supported deterioration/trend path when enough business cues are present
  - `2A` broaden peer/comparison routing with richer relative-language cues, but do not infer peer mode from multiple tickers alone
  - `3A` narrow to the prompt-named subset when the symbols are already in the workspace; if symbols are outside the workspace, stop and guide instead of silently expanding
  - `4A` replace dead-end unsupported failures with 2-3 concrete rewrite suggestions
  - `5A` keep routing deterministic-first, with only an explicit audited LLM rescue fallback if enabled later
- The user explicitly wants normal analyst wording to work, but not at the cost of hidden scope changes or opaque model-led routing.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Scope and acceptance criteria
- `.planning/PROJECT.md` — v1.2 milestone framing, current product bottlenecks, and deterministic trust constraints
- `.planning/ROADMAP.md` — Phase 13 goal, dependency on Phase 12, and the three success criteria for analyst prompt routing
- `.planning/REQUIREMENTS.md` — `PROMPT-01`, `PROMPT-02`, and `PROMPT-03` define the formal acceptance criteria
- `.planning/STATE.md` — current project position after Phase 12 completion

### Prior decisions that constrain this phase
- `.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md` — chat remains sync-first for now and should stay truthful about what execution path was used
- `.planning/phases/01-run-isolation/01-CONTEXT.md` — run-scoped execution and explicit path contracts remain canonical
- `.planning/phases/03-secure-defaults/03-CONTEXT.md` — defaults should remain safe and explicit, which constrains any LLM rescue behavior

### Current prompt-routing and failure seams
- `edgar_project/orchestration/intent.py` — current deterministic coarse intent gate and its current narrow regex/token rules
- `edgar_project/orchestration/goal_preferences.py` — richer business-cue parsing that only helps after intent has already matched
- `edgar_project/orchestration/planner.py` — unsupported-goal failure path and deterministic template selection boundary
- `tests/orchestration/test_intent.py` — current deterministic intent examples and unsupported baseline
- `tests/orchestration/test_planner.py` — current planner expectations for anomaly, peer, and pipeline routes
- `tests/orchestration/test_planner_alignment_regression.py` — current regression anchors tied to user-facing goal phrasing

### Current product-facing prompt examples and chat entry path
- `frontend/src/lib/analysis-examples.ts` — current curated example prompts already tuned around what routing understands
- `frontend/src/components/analysis/analysis-composer-fields.tsx` — user-facing hint text about what kinds of goals the planner handles well
- `frontend/src/actions/runs.ts` — current chat submit flow and the place where unsupported planner failures surface back to the user
- `frontend/src/components/chat-shell/chat-shell.tsx` — current chat frame where prompt-routing failures will ultimately need to feel usable

### Optional LLM rescue seam
- `backend/config/settings.py` — current `orchestration_llm_intent_assistance` flag and related model configuration
- `backend/services/edgar_pipeline_execution_service.py` — current execution path where optional intent-preference assistance is applied
- `backend/agents/intent_preferences_assistant.py` — current model-assisted preference patch path that only runs after deterministic routing has a valid intent
- `tests/test_intent_preferences_assistant.py` — current expectations for deterministic planner plus optional preference assistance
- `tests/test_llm_output_quality_regression.py` — existing regression anchors for model-assisted intent/planning quality fixtures

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `goal_preferences.py` already extracts deterioration, trend, peer, persistence, metric, and time-horizon cues from normal analyst phrasing, so Phase 13 can likely reuse that signal instead of inventing a separate semantic layer from scratch.
- `tests/orchestration/test_planner_alignment_regression.py` already anchors several user-facing phrasing examples that map onto trend deterioration, one-off anomaly, peer comparison, and mixed routing.
- `analysis-examples.ts` and `analysis-composer-fields.tsx` already contain product copy about what the planner handles well, which can be updated to stay aligned with any routing expansion or rewrite-guidance surface.
- The existing optional model-assisted preference path is already isolated and auditable, so if Phase 13 introduces any LLM rescue behavior it has an existing seam to extend rather than requiring a new trust boundary from scratch.

### Established Patterns
- Routing is currently two-stage but gated too early: `intent.py` decides whether the prompt is supported at all, then `goal_preferences.py` and `plan_templates.py` refine how to route within the supported surface.
- Broad deterioration and thesis-style prompts can already work once intent is classified, but many natural prompts fail because the coarse intent gate only recognizes a narrow set of anomaly/compare/pipeline phrases.
- The current unsupported path is technically informative (`Unsupported analysis_goal; no supported intent matched.` plus supported intent ids) but not product-usable.
- Chat currently submits the user’s full workspace ticker set unless another layer narrows it, so prompt text that names only one company can be semantically ignored today.

### Integration Points
- Deterministic routing changes will primarily touch `intent.py`, planner failure reporting in `planner.py`, and the regression suite under `tests/orchestration/`.
- Prompt-named subset handling will need to connect the chat-side workspace scope with orchestration inputs so named in-scope symbols can narrow the run without breaking the workspace contract.
- Unsupported guidance likely needs coordinated backend and frontend changes so the failure can carry concrete rewrite suggestions rather than only a generic error string.
- Any optional LLM rescue path must stay behind explicit configuration in `backend/config/settings.py` and leave audit traces in the same style as the existing intent-preferences assistant.

</code_context>

<deferred>
## Deferred Ideas

- Chat-native answer rendering and result message schema — Phase 14
- Evidence navigation and compact artifact/trace rail in chat — Phase 15
- Simplified standalone run page as a secondary inspection surface — Phase 16
- Any new analytical workflows beyond the current supported deterioration/trend, anomaly, and peer-comparison modes

</deferred>

---

*Phase: 13-analyst-prompt-routing*
*Context gathered: 2026-04-18*
