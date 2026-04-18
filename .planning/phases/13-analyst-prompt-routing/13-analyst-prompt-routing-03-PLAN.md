---
phase: 13-analyst-prompt-routing
plan: 03
type: execute
wave: 3
depends_on:
  - 02
files_modified:
  - frontend/src/lib/api/types.ts
  - frontend/src/lib/api/runs.ts
  - frontend/src/actions/runs.ts
  - frontend/src/actions/runs.test.ts
  - frontend/src/components/chat-shell/types.ts
  - frontend/src/components/chat-shell/chat-message-list.tsx
  - frontend/src/components/chat-shell/chat-message-list.test.tsx
  - frontend/src/lib/analysis-examples.ts
  - frontend/src/components/analysis/analysis-composer-fields.tsx
autonomous: true
requirements:
  - PROMPT-01
  - PROMPT-02
  - PROMPT-03
must_haves:
  truths:
    - "Workspace chat previews routing before run creation, so unsupported prompts return guidance inline instead of becoming failed runs."
    - "Unsupported chat replies show rewrite suggestions and scope guidance without run links."
    - "The product’s example prompts and composer hints reflect the deterministic routing surface that now actually works."
  artifacts:
    - path: frontend/src/actions/runs.ts
      provides: "Preview-before-create chat action with unsupported guidance branch"
    - path: frontend/src/components/chat-shell/chat-message-list.tsx
      provides: "Inline rendering for rewrite suggestions without dead-end navigation links"
    - path: frontend/src/lib/analysis-examples.ts
      provides: "Examples aligned to the expanded analyst-language routing surface"
  key_links:
    - from: frontend/src/actions/runs.ts
      to: frontend/src/lib/api/runs.ts
      via: "Chat action calls `route-preview` before `createRun` and `executeRun`"
      pattern: "getPromptRoutingPreview|createRun|executeRun"
    - from: frontend/src/actions/runs.ts
      to: frontend/src/components/chat-shell/chat-message-list.tsx
      via: "Unsupported preview responses become assistant messages with rewrite suggestions instead of run links"
      pattern: "rewriteSuggestions|runHref|deepDiveHref"
    - from: frontend/src/lib/analysis-examples.ts
      to: frontend/src/components/analysis/analysis-composer-fields.tsx
      via: "Example prompts and planner-hint text stay aligned to the routing surface exposed to users"
      pattern: "temporary or structural|versus|weaker"
---

<objective>
Use the deterministic preview contract in chat, render unsupported guidance inline, and align product examples with the broadened analyst-language routing surface.

Purpose: complete the user-facing Phase 13 behavior so supported prompts run cleanly and unsupported prompts get usable rewrites before execution.
Output: preview-before-create chat flow, inline unsupported guidance, and updated example/hint copy.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
@.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
@.planning/phases/13-analyst-prompt-routing/13-VALIDATION.md
@frontend/src/lib/api/types.ts
@frontend/src/lib/api/runs.ts
@frontend/src/actions/runs.ts
@frontend/src/components/chat-shell/types.ts
@frontend/src/components/chat-shell/chat-message-list.tsx
@frontend/src/lib/analysis-examples.ts
@frontend/src/components/analysis/analysis-composer-fields.tsx
@frontend/src/components/chat-shell/chat-message-list.test.tsx
@frontend/src/components/chat-shell/chat-shell.test.tsx
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Preview routing before run creation and return unsupported guidance as a chat reply</name>
  <files>frontend/src/lib/api/types.ts
frontend/src/lib/api/runs.ts
frontend/src/actions/runs.ts
frontend/src/actions/runs.test.ts
frontend/src/components/chat-shell/types.ts</files>
  <read_first>.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
frontend/src/lib/api/types.ts
frontend/src/lib/api/runs.ts
frontend/src/actions/runs.ts
frontend/src/components/chat-shell/types.ts</read_first>
  <behavior>
    - Chat must call the new route-preview API before creating a run.
    - Unsupported prompts must return an assistant reply with guidance instead of creating or executing a run.
    - Supported prompts must still follow the existing synchronous create-and-execute path.
  </behavior>
  <action>Add a typed preview helper to `frontend/src/lib/api/runs.ts` and matching request/response interfaces to `frontend/src/lib/api/types.ts` for `POST /v1/runs/route-preview`. In `frontend/src/actions/runs.ts`, call that preview helper first using the current `projectId`, `goal`, `tickers`, and `refresh`. If the preview response says `supported=false`, return a `reply` object immediately with assistant content such as `I couldn't route that request yet.` plus the preview `rewrite_suggestions`, the preview `reason`, and no `runId`, `runHref`, `deepDiveHref`, or `runsHref`. If the preview response says `supported=true`, keep the current `createRun(...)` + `executeRun(...)` flow, but use `effective_tickers` from the preview response instead of blindly sending the full workspace scope. Extend the chat message types in `frontend/src/components/chat-shell/types.ts` so assistant messages can carry `rewriteSuggestions` and an optional `routingReason`. Add `frontend/src/actions/runs.test.ts` that mocks the preview helper, `createRun`, and `executeRun`, then proves the unsupported branch returns rewrite suggestions and does not call `createRun(...)` or `executeRun(...)`, while the supported branch still does.</action>
  <acceptance_criteria>`frontend/src/lib/api/runs.ts` contains `getPromptRoutingPreview`.
`frontend/src/lib/api/types.ts` contains `PromptRoutingPreviewResponse`.
`frontend/src/actions/runs.ts` contains `getPromptRoutingPreview`.
`frontend/src/actions/runs.ts` contains `effective_tickers`.
`frontend/src/actions/runs.ts` contains `rewriteSuggestions`.
`frontend/src/actions/runs.ts` contains `I couldn't route that request yet.` or another fixed unsupported-reply string.
`frontend/src/components/chat-shell/types.ts` contains `rewriteSuggestions`.
`frontend/src/actions/runs.test.ts` exists.
`frontend/src/actions/runs.test.ts` contains `createRun`.
`frontend/src/actions/runs.test.ts` contains `executeRun`.
`frontend/src/actions/runs.test.ts` contains `rewriteSuggestions`.
`cd frontend && npm run test -- src/actions/runs.test.ts` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/actions/runs.test.ts</automated>
  </verify>
  <done>Unsupported prompts are stopped before execution and come back to chat as actionable assistant guidance rather than failed runs.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Render rewrite suggestions inline and align example prompts with the expanded routing surface</name>
  <files>frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/lib/analysis-examples.ts
frontend/src/components/analysis/analysis-composer-fields.tsx</files>
  <read_first>.planning/phases/13-analyst-prompt-routing/13-CONTEXT.md
.planning/phases/13-analyst-prompt-routing/13-RESEARCH.md
frontend/src/components/chat-shell/chat-message-list.tsx
frontend/src/components/chat-shell/chat-message-list.test.tsx
frontend/src/lib/analysis-examples.ts
frontend/src/components/analysis/analysis-composer-fields.tsx</read_first>
  <behavior>
    - Unsupported assistant replies should render rewrite suggestions as actionable inline guidance.
    - Unsupported chat messages must not show dead-end run links when no run exists.
    - Product examples and hint text should visibly reflect the broadened analyst-language routing that Phase 13 now supports.
  </behavior>
  <action>Update `frontend/src/components/chat-shell/chat-message-list.tsx` so assistant messages with `rewriteSuggestions` render a compact list under the assistant content and do not render `Run answer`, `Deep dive`, or `All runs` links when `runHref`, `deepDiveHref`, and `runsHref` are absent. Extend `frontend/src/components/chat-shell/chat-message-list.test.tsx` with an unsupported-routing case that asserts the rewrite suggestions appear and the run links do not. Then refresh `frontend/src/lib/analysis-examples.ts` and the planner hint text in `frontend/src/components/analysis/analysis-composer-fields.tsx` so at least one example uses the exact analyst-language phrasing `whether margin pressure is temporary or structural`, and at least one comparison example uses ordinary relative language such as `Which company is weaker` or `AAPL versus MSFT`. Keep the examples within the existing supported analytical surface and do not add new capabilities beyond deterioration/trend, anomaly, and peer comparison.</action>
  <acceptance_criteria>`frontend/src/components/chat-shell/chat-message-list.tsx` contains `rewriteSuggestions`.
`frontend/src/components/chat-shell/chat-message-list.tsx` contains a conditional branch that checks for missing run links.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` contains an unsupported-routing case with `rewriteSuggestions`.
`frontend/src/components/chat-shell/chat-message-list.test.tsx` asserts `Run answer` is absent or not rendered for that case.
`frontend/src/lib/analysis-examples.ts` contains `temporary or structural`.
`frontend/src/lib/analysis-examples.ts` contains `versus` or `Which company is weaker`.
`frontend/src/components/analysis/analysis-composer-fields.tsx` contains `temporary or structural` or `weaker`.
`cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx` passes.</acceptance_criteria>
  <verify>
    <automated>cd frontend && npm run test -- src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx</automated>
  </verify>
  <done>Chat visibly guides unsupported users toward working phrasing, and the product examples now show the phrases the planner genuinely supports.</done>
</task>

</tasks>

<verification>
Run `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx && npm run build` after both tasks land.
</verification>

<success_criteria>
Phase 13 is product-complete once chat previews routing before execution, unsupported prompts return inline rewrite guidance instead of dead-end runs, and the visible examples match the analyst-language prompts that now work.
</success_criteria>

<output>
After completion, create `.planning/phases/13-analyst-prompt-routing/13-analyst-prompt-routing-03-SUMMARY.md`
</output>
