# Phase 13: Analyst Prompt Routing - Research

**Researched:** 2026-04-18
**Domain:** Deterministic analyst-language routing, prompt-scoped ticker narrowing, actionable unsupported guidance, and an explicit no-surprises LLM-rescue boundary
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Broad analyst theses like “is margin pressure temporary or structural?” or “is cash flow quality slipping?” should map to the closest supported deterioration or trend route when enough business cues are present.
- **D-02:** Phase 13 should make normal analyst language work without requiring explicit anomaly or deterioration keywords in every successful prompt.
- **D-03:** Peer routing should accept broader relative-language cues such as `vs`, `versus`, `relative to`, `weaker`, `stronger`, and `underperform`.
- **D-04:** Multiple tickers alone must not force peer mode; peer routing still needs explicit relative/comparison language.
- **D-05:** If the prompt names a subset of companies already in the workspace, the run should narrow to that subset instead of silently using the whole workspace scope.
- **D-06:** If the prompt names symbols outside the workspace scope, the product should stop and return guidance instead of silently expanding scope.
- **D-07:** Unsupported routing should return 2-3 concrete rewrite suggestions shaped around the current prompt and workspace scope.
- **D-08:** Unsupported handling should become a usable next-step surface, not just a technical unsupported-intent error.
- **D-09:** Routing remains deterministic-first by default.
- **D-10:** Any model-assisted rescue path must be explicit, config-gated, and auditable when it is used after deterministic routing fails.

### the agent's Discretion
- Exact deterministic cue expansion in `intent.py` and whether to reuse a shared prompt-scope helper
- Exact preview/guidance contract used between backend routing and chat
- Exact rewrite-suggestion phrasing, as long as it is concrete and tied to the current workspace scope
- Exact place to enforce prompt-named ticker narrowing, as long as the workspace contract remains canonical

### Deferred Ideas (OUT OF SCOPE)
- Chat-native answer rendering and run-message schema
- Evidence or artifact navigation attached to chat answers
- Standalone run-page simplification
- New analytical workflows beyond the existing deterioration/trend, anomaly, and peer-comparison surface
- Default-on model-assisted routing rescue
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PROMPT-01 | User can submit common single-company deterioration or anomaly requests in normal analyst phrasing without unsupported-intent failures | The deterministic routing gate should widen beyond anomaly keywords and accept thesis-style business cues such as margin pressure, cash-flow quality, persistence, direction, and recent-quarter framing. |
| PROMPT-02 | User can submit common peer-comparison requests in normal analyst phrasing without unsupported-intent failures | Peer routing should recognize ordinary comparison language such as `vs`, `versus`, `relative to`, `weaker`, `stronger`, and `underperform`, while refusing to infer peer mode from multiple tickers alone. |
| PROMPT-03 | When a request still cannot map to a supported analysis path, user sees actionable rewrite guidance instead of a dead-end error | Unsupported prompts should be previewed before run creation in the chat path, and the deterministic planner should return concrete rewrite suggestions and scope guidance rather than only “supported intent ids”. |
</phase_requirements>

## Summary

Phase 13 is mostly a boundary problem, not a new-analysis problem. The repo already knows how to route rich analyst intent once a prompt gets past the coarse gate: `goal_preferences.py` extracts deterioration, persistence, metric, and time-horizon cues, and `plan_templates.py` already turns those preferences into the correct `run_pipeline` vs granular plan shape. The brittle seam is earlier. `intent.py` only admits a narrow set of anomaly, compare-report, or explicit pipeline phrases, so otherwise-valid analyst asks fail before the richer routing layer can help.

That mismatch is now a product bug because the current workspace UI already invites broader language. The curated examples in `frontend/src/lib/analysis-examples.ts` use prompts like “operating margin and free cash flow margin; highlight relative pressure over the last eight quarters” and “Assess cash conversion vs net income and capex intensity”, yet the deterministic gate still prefers prompts with words like `unusual`, `anomaly`, `compare ... generate a report`, or `run the pipeline`. The result is the exact failure the user hit: a normal analyst sentence creates a run, the run executes far enough to fail planning, and the user is pushed onto an error-heavy run page instead of getting immediate rewrite guidance in chat.

The safest brownfield move is to keep the current coarse intent enum and widen its eligibility rules instead of inventing a new planner model or a new intent taxonomy. `OrchestrationIntent` only needs to answer three product questions right now: “Is this a pipeline-wide company analysis request?”, “Is this a peer/comparison request?”, or “Is this the anomaly/trend/deterioration bucket?” Phase 13 should therefore broaden the `anomaly_analysis` gate to admit analyst-language deterioration/trend theses when enough business cues are present, and broaden `peer_report` to accept ordinary comparative language when the prompt clearly asks for relative judgment.

Prompt-scoped ticker handling belongs in the orchestration input boundary, not the chat UI alone. Today the chat action submits the workspace tickers as a hidden field and the backend planner blindly uses all of them. That means a prompt like “Analyze MSFT over the last 8 quarters...” can be semantically ignored if the workspace currently contains `AAPL`, `MSFT`, and `NVDA`. The product decision is explicit: when the prompt names a subset already in the workspace, narrow to that subset; when it names symbols outside the workspace, stop and guide instead of silently expanding. The cleanest way to enforce that across chat and any future backend callers is a small deterministic helper at the orchestration boundary that extracts uppercase ticker tokens from the prompt, intersects them with `request.tickers`, and surfaces out-of-scope mentions as routing guidance.

The unsupported-guidance problem should be solved before run creation on the chat path. Right now `createAnalysisRunFromChat(...)` posts a real run and then executes it synchronously; if the planner rejects the goal, the user has already created a failed run row. That is technically recoverable but poor product behavior. An additive preview endpoint such as `POST /v1/runs/route-preview` is the lowest-risk fix: it can call the deterministic planner on the proposed goal and workspace tickers, return `supported=true` with the effective narrowed tickers and interpreted goal when routing succeeds, or return `supported=false` with concrete rewrite suggestions and scope guidance when routing fails. Chat can then stop before run creation on the unsupported path without breaking the existing create/execute APIs.

The LLM-rescue boundary should stay explicit and mostly untouched in Phase 13. The repo already has one optional model-assisted seam, `orchestration_llm_intent_assistance`, but that only patches `GoalPreferences` after a deterministic intent already exists. The user’s decision here is architectural, not necessarily a new requirement: Phase 13 should keep the default routing source deterministic and make any future rescue path explicit, config-gated, and auditable. The simplest way to honor that is for the new preview/guidance contract to surface `routing_source="deterministic"` now, without introducing hidden model calls. If a later phase or follow-up adds actual rescue behavior, that response contract and audit surface are already ready.

**Primary recommendation:** plan Phase 13 as **3 sequential plans**. First, widen deterministic routing and add prompt-scoped ticker narrowing in the orchestration layer. Second, add a structured deterministic preview/guidance contract so unsupported prompts return concrete next phrasing without creating a failed run. Third, use that contract in chat, render rewrite suggestions inline, and align example prompts and tests with the newly supported analyst language. That shape satisfies `PROMPT-01`, `PROMPT-02`, and `PROMPT-03` without broadening into chat-answer rendering or model-led routing.

## Standard Stack

### Core

| Library / Seam | Version | Purpose | Why Standard |
|----------------|---------|---------|--------------|
| `edgar_project/orchestration/intent.py` | in-repo seam | Coarse deterministic intent eligibility for supported prompts | This is the current gate that must be widened without changing the planner’s trust model. |
| `edgar_project/orchestration/goal_preferences.py` | in-repo seam | Rich business-cue parsing for deterioration, persistence, metrics, time, and peer expectations | The richer cue layer already exists and should be reused instead of reimplemented. |
| `edgar_project/orchestration/planner.py` | in-repo seam | Shared deterministic planning and unsupported-failure contract | This is the right place to centralize scope narrowing and rewrite guidance so chat and non-chat callers stay aligned. |
| FastAPI route layer in `backend/api/routes/runs.py` | in-repo seam | Add a routing preview endpoint without breaking create/execute semantics | The project already uses small additive routes for run lifecycle and health surfaces. |
| `frontend/src/actions/runs.ts` | in-repo seam | Stop unsupported prompts before run creation and return guidance in chat | The server action already owns chat submit behavior, so Phase 13 can improve the product without adding client-side direct API calls. |

### Supporting

| Library / Seam | Version | Purpose | When to Use |
|----------------|---------|---------|-------------|
| `frontend/src/lib/analysis-examples.ts` | in-repo seam | Keep example prompts aligned with the actual supported routing surface | Use after the deterministic routing rules are widened so the product copy stays honest. |
| `frontend/src/components/analysis/analysis-composer-fields.tsx` | in-repo seam | Update hint text about what the planner understands well | Use for small copy alignment once the backend contract is clear. |
| `tests/orchestration/test_intent.py` | in-repo seam | Lock pure intent eligibility behavior | Use for phrase-level routing coverage. |
| `tests/orchestration/test_planner_alignment_regression.py` | in-repo seam | Lock user-facing prompts to the correct templates and preference outcomes | Use for regression anchors tied to product examples and live user prompts. |
| Vitest component/action tests in `frontend/src/components/chat-shell/` | in-repo seam | Verify chat shows guidance rather than dead-end links | Use for the chat-facing delivery of the new preview contract. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Widening deterministic routing and adding a deterministic preview contract | Default-on model-assisted routing rescue | Faster apparent coverage, but it weakens the trust boundary and makes ordinary analyst prompts depend on hidden model behavior. |
| Planner-level prompt-scope narrowing | Chat-only string parsing before submission | Simpler for the current UI, but it would leave CLI/API callers inconsistent and silently reintroduce the bug outside chat. |
| Additive `route-preview` endpoint | Validate inside `POST /v1/runs` and reject run creation there | Fewer routes, but it changes the semantics of a generic persistence API and makes brownfield compatibility riskier. |

## Recommended Patterns

### Pattern 1: Broaden Deterministic Routing at the Eligibility Gate, Not the Intent Enum

**What:** Keep `OrchestrationIntent` as `anomaly_analysis`, `peer_report`, and `full_pipeline_run`, but admit more analyst-language prompts into those buckets.

**When to use:** Every normal analyst prompt submitted through workspace chat or the generic orchestration entrypoint.

**Why:** The current planner already knows how to turn deterioration, trend, peer, and mixed preferences into the correct plan template. The enum is not the problem; the eligibility gate is.

**Recommended deterministic cues:**
- Single-company or subset theses should match `anomaly_analysis` when the goal includes business language like `margin pressure`, `cash flow quality`, `deterioration`, `slipping`, `temporary or structural`, `persistent`, `sustained`, `last eight quarters`, or named metrics from `goal_preferences.py`.
- Peer prompts should match `peer_report` when the goal includes explicit comparative cues like `vs`, `versus`, `relative to`, `weaker`, `stronger`, `underperform`, `outperform`, or `which company`, especially when paired with two or more in-scope tickers.
- Multiple tickers alone should remain neutral; they do not imply peer routing unless comparison language is present.

### Pattern 2: Ticker Narrowing Should Happen on the Orchestration Input, Not Only in Chat

**What:** Add a deterministic prompt-scope helper that extracts named ticker symbols from `analysis_goal` and compares them against `request.tickers`.

**When to use:** Before plan-template selection in `Planner.build_plan(...)`.

**Why:** The chat UI currently submits the whole workspace scope. If narrowing only happens in the UI, other callers will drift and the planner will still ignore prompt-named subsets.

**Recommended behavior:**
- If the prompt names one or more ticker symbols already present in `request.tickers`, narrow the effective run scope to only those symbols.
- If the prompt names one or more ticker symbols that are not present in `request.tickers`, stop and mark the request unsupported for the current scope.
- Do not silently add named out-of-scope tickers to the run.
- Do not attempt fuzzy company-name-to-ticker resolution in this phase; explicit ticker-symbol matching is the reliable brownfield move.

### Pattern 3: Unsupported Guidance Should Be Previewed Before Run Creation

**What:** Add a lightweight preview endpoint for the chat path that calls the deterministic planner on the proposed goal and workspace tickers without creating a run row.

**When to use:** `createAnalysisRunFromChat(...)` before `createRun(...)`.

**Why:** The current unsupported path creates a failed run and forces the user onto a run error surface. Chat needs to stop earlier and return usable rewrite guidance instead.

**Recommended contract:**
- Request: `project_id`, `analysis_goal`, `tickers`, optional `refresh`
- Success response fields: `supported`, `routing_source`, `effective_tickers`, `intent`, `goal_code`, `plan_template_id`
- Unsupported response fields: `supported`, `routing_source`, `reason`, `out_of_scope_tickers`, `rewrite_suggestions`
- `routing_source` should be `"deterministic"` in Phase 13

### Pattern 4: Rewrite Suggestions Must Be Concrete and Situation-Aware

**What:** Build deterministic rewrite suggestions from the failed prompt shape and workspace scope instead of returning only intent IDs or generic help text.

**When to use:** Unsupported routing, including out-of-scope symbol mentions.

**Why:** The product requirement is not “better diagnostics”; it is “usable next-step guidance.”

**Recommended suggestion families:**
- If the user asked a single-company thesis without enough cues, suggest a deterioration/trend phrasing like:  
  `Detect any signs of financial deterioration in MSFT over recent quarters. Focus on margin pressure, revenue growth, and cash flow quality.`
- If the user asked a comparison without explicit comparison cues, suggest a peer phrasing like:  
  `Compare AAPL and MSFT to peers on operating margin and free cash flow margin; highlight relative pressure over the last eight quarters.`
- If the prompt names out-of-scope symbols, include a scope-specific suggestion like:  
  `Your workspace scope is AAPL, MSFT, NVDA. Either update the workspace scope to include TSLA or rewrite the question using the current symbols.`

### Pattern 5: Make the Deterministic Trust Boundary Explicit

**What:** Surface a routing-source field and keep model-assisted rescue out of the default Phase 13 path.

**When to use:** Preview responses, planner guidance, and any future routing rescue extension.

**Why:** The user explicitly chose deterministic-first routing. The product should not silently switch to model-led rescue.

**Recommended Phase 13 stance:**
- Use `routing_source="deterministic"` everywhere in the preview and guidance responses.
- Do not call `maybe_apply_llm_intent_preferences(...)` from the new preview route.
- Do not add a default-on LLM routing rescue in this phase.
- If a later phase introduces rescue, keep it behind explicit configuration and record when it was used.

## Implementation Slices

### Slice A: Deterministic Routing Expansion and Prompt Scope Foundation

Focus files:
- `edgar_project/orchestration/intent.py`
- `edgar_project/orchestration/planner.py`
- `edgar_project/orchestration/prompt_scope.py`
- `tests/orchestration/test_intent.py`
- `tests/orchestration/test_planner.py`
- `tests/orchestration/test_planner_alignment_regression.py`
- `tests/orchestration/test_prompt_scope.py`

Deliver:
- thesis-style single-company prompts route without anomaly-specific wording
- peer prompts accept broader relative language without inferring peer mode from multiple tickers alone
- prompt-named in-workspace ticker subsets narrow the effective run scope
- prompt-named out-of-scope symbols are detected deterministically for guidance

### Slice B: Deterministic Preview and Unsupported Guidance Contract

Focus files:
- `edgar_project/orchestration/schemas.py`
- `edgar_project/orchestration/planner.py`
- `backend/schemas/prompt_routing.py`
- `backend/api/routes/runs.py`
- `tests/orchestration/test_planner.py`
- `tests/test_prompt_routing_api.py`

Deliver:
- structured rewrite suggestions from the deterministic planner
- additive `POST /v1/runs/route-preview` backend contract
- preview responses that explicitly expose `routing_source="deterministic"`
- no failed run row creation on the unsupported chat path

### Slice C: Chat Integration, Product Copy Alignment, and Regression Hardening

Focus files:
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/actions/runs.ts`
- `frontend/src/actions/runs.test.ts`
- `frontend/src/components/chat-shell/types.ts`
- `frontend/src/components/chat-shell/chat-message-list.tsx`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/lib/analysis-examples.ts`
- `frontend/src/components/analysis/analysis-composer-fields.tsx`

Deliver:
- chat calls the preview route before creating a run
- unsupported prompts render actionable rewrite suggestions inline instead of dead-end run links
- example prompts and composer hint text match the newly supported analyst phrasing
- regression coverage proves unsupported previews do not call `createRun(...)`

## Validation Architecture

Phase 13 needs both orchestration and chat-layer validation because the routing fix crosses pure planner logic, a new backend preview contract, and the workspace submit path.

**Recommended quick command:**
```bash
python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py tests/test_prompt_routing_api.py -q --tb=short && cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx
```

**Recommended full command:**
```bash
python3 -m pytest tests/orchestration/test_intent.py tests/orchestration/test_planner.py tests/orchestration/test_planner_alignment_regression.py tests/orchestration/test_phase3_orchestration.py tests/orchestration/test_prompt_scope.py tests/test_prompt_routing_api.py tests/test_intent_preferences_assistant.py -q --tb=short && cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build
```

**Required new or extended tests:**
- `tests/orchestration/test_intent.py`
  - thesis-style single-company prompts route into the supported coarse intent
  - peer language like `vs`, `versus`, `weaker`, and `underperform` routes to `peer_report`
  - multiple tickers without comparison language do not force `peer_report`
- `tests/orchestration/test_prompt_scope.py`
  - in-scope ticker mentions narrow the effective run scope
  - out-of-scope ticker mentions are surfaced for guidance instead of silently expanding
- `tests/orchestration/test_planner_alignment_regression.py`
  - live user prompt “Analyze MSFT over the last 8 quarters and tell me whether margin pressure is temporary or structural” maps to the deterioration/trend template
  - additional peer-relative prompt regressions stay aligned with `peer_comparison`
- `tests/test_prompt_routing_api.py`
  - preview returns `supported=true` with narrowed `effective_tickers`
  - preview returns `supported=false` with `rewrite_suggestions` and `routing_source="deterministic"`
  - preview requires project ownership
- `frontend/src/actions/runs.test.ts`
  - unsupported preview returns a chat reply with rewrite suggestions
  - unsupported preview does not call `createRun(...)` or `executeRun(...)`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
  - assistant messages render rewrite suggestions without run links on the unsupported path

## Pitfalls and Boundaries

- Do not add a new intent enum just to represent deterioration or trend asks; the planner already handles those through preferences and templates.
- Do not infer peer mode from multiple tickers alone.
- Do not silently add prompt-named out-of-scope symbols to a workspace run.
- Do not solve subset narrowing with chat-only parsing; the orchestration boundary must enforce the same rule.
- Do not keep unsupported guidance trapped inside a failed run row when the chat path can preview it first.
- Do not introduce a hidden model-assisted routing rescue as part of this phase.

## Recommended Plan Shape

Phase 13 should be planned as **3 sequential plans**:

1. **Deterministic routing foundation** — widen supported analyst phrasing and add prompt-scoped ticker narrowing
2. **Preview and guidance contract** — add deterministic rewrite suggestions and a `route-preview` backend endpoint
3. **Chat integration and product alignment** — use preview-before-create in chat, render rewrite suggestions inline, and align example prompts/copy

This sequence keeps the routing core first, the backend contract second, and the chat-facing product behavior last.

## Sources

### Primary
- `.planning/PROJECT.md`
- `.planning/ROADMAP.md`
- `.planning/REQUIREMENTS.md`
- `.planning/STATE.md`
- `.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md`
- `.planning/phases/12-runtime-reliability-for-chat-delivery/12-CONTEXT.md`
- `edgar_project/orchestration/intent.py`
- `edgar_project/orchestration/goal_preferences.py`
- `edgar_project/orchestration/planner.py`
- `edgar_project/orchestration/plan_templates.py`
- `edgar_project/orchestration/schemas.py`
- `backend/api/routes/runs.py`
- `backend/config/settings.py`
- `backend/agents/intent_preferences_assistant.py`
- `frontend/src/actions/runs.ts`
- `frontend/src/lib/analysis-examples.ts`
- `frontend/src/components/analysis/analysis-composer-fields.tsx`
- `frontend/src/components/chat-shell/chat-shell.tsx`
- `frontend/src/components/chat-shell/chat-message-list.tsx`

### Tests and regression anchors
- `tests/orchestration/test_intent.py`
- `tests/orchestration/test_planner.py`
- `tests/orchestration/test_planner_alignment_regression.py`
- `tests/orchestration/test_phase3_orchestration.py`
- `tests/test_intent_preferences_assistant.py`
- `frontend/src/components/chat-shell/chat-composer.test.tsx`
- `frontend/src/components/chat-shell/chat-message-list.test.tsx`
- `frontend/src/components/chat-shell/chat-shell.test.tsx`
