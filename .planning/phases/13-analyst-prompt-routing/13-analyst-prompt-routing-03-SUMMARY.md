---
phase: 13-analyst-prompt-routing
plan: 03
subsystem: frontend
tags: [nextjs, chat, routing, guidance, vitest]
requires:
  - phase: 13-analyst-prompt-routing
    plan: 02
    provides: "A project-scoped deterministic route-preview API and structured planner guidance for supported and unsupported prompts"
provides:
  - "Preview-before-create chat flow that stops unsupported prompts before run creation"
  - "Inline rewrite suggestions and routing reasons for unsupported chat replies without dead-end run links"
  - "Examples and composer hints aligned to the supported deterministic analyst-language routing surface"
affects: [frontend, chat, onboarding, tests]
tech-stack:
  added: []
  patterns: ["preview-before-create chat submission", "inline unsupported routing guidance", "product examples aligned to deterministic planner coverage"]
key-files:
  created:
    - .planning/phases/13-analyst-prompt-routing/13-analyst-prompt-routing-03-SUMMARY.md
    - frontend/src/actions/runs.test.ts
  modified:
    - frontend/src/lib/api/types.ts
    - frontend/src/lib/api/runs.ts
    - frontend/src/actions/runs.ts
    - frontend/src/components/chat-shell/types.ts
    - frontend/src/components/chat-shell/chat-message-list.tsx
    - frontend/src/components/chat-shell/chat-message-list.test.tsx
    - frontend/src/components/chat-shell/chat-shell.tsx
    - frontend/src/lib/analysis-examples.ts
    - frontend/src/components/analysis/analysis-composer-fields.tsx
key-decisions:
  - "Chat now calls the deterministic route-preview contract before run creation so unsupported prompts fail early in the same conversation rather than creating a doomed run row."
  - "Unsupported assistant replies render routing reasons and rewrite suggestions inline and suppress run navigation when no run exists."
patterns-established:
  - "Supported chat prompts use preview `effective_tickers` rather than blindly reusing the full workspace scope."
  - "Visible example prompts and composer hint text now mirror the exact deterioration and relative-language phrasing the deterministic planner accepts."
requirements-completed: [PROMPT-01, PROMPT-02, PROMPT-03]
duration: 8 min
completed: 2026-04-18
---

# Phase 13 Plan 03: Analyst Prompt Routing Summary

**Chat previews routing before execution, renders unsupported guidance inline, and shows only examples that the deterministic planner actually supports**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-18T22:52:21Z
- **Completed:** 2026-04-18T23:57:24Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments

- Added a typed `route-preview` helper to the frontend API layer and made chat preview routing before calling `createRun(...)` or `executeRun(...)`.
- Stopped unsupported prompts before run creation and returned an assistant reply with `rewriteSuggestions` and `routingReason` instead of dead-end run links.
- Passed the new routing guidance through chat state so unsupported replies render inline suggestions and hide run navigation when no run exists.
- Updated visible prompt examples and planner hint text to use supported thesis-style and relative-language phrasing such as `temporary or structural`, `versus`, and `which company is weaker`.

## Task Commits

Each task was committed atomically through the TDD cycle:

1. **Task 1 RED: chat route-preview tests** - `31d38f7` (`test`)
2. **Task 1 GREEN: preview-before-create chat flow** - `b4ee304` (`feat`)
3. **Task 2 RED: unsupported chat guidance tests** - `00cefe7` (`test`)
4. **Task 2 GREEN: inline unsupported guidance and aligned examples** - `3693c7e` (`feat`)

## Files Created/Modified

- `frontend/src/lib/api/types.ts` - Adds the typed `PromptRoutingPreviewRequest` and `PromptRoutingPreviewResponse` contract used by chat.
- `frontend/src/lib/api/runs.ts` - Adds `getPromptRoutingPreview(...)` for `POST /v1/runs/route-preview`.
- `frontend/src/actions/runs.ts` - Previews routing before run creation, short-circuits unsupported requests into assistant guidance, and uses preview `effective_tickers` for supported runs.
- `frontend/src/actions/runs.test.ts` - Locks unsupported preview behavior, verifies `createRun(...)`/`executeRun(...)` are skipped on unsupported prompts, and confirms supported prompts use narrowed `effective_tickers`.
- `frontend/src/components/chat-shell/types.ts` - Extends assistant messages with `rewriteSuggestions` and `routingReason`.
- `frontend/src/components/chat-shell/chat-message-list.tsx` - Renders inline rewrite suggestions and routing reasons while hiding run links when no run exists.
- `frontend/src/components/chat-shell/chat-message-list.test.tsx` - Covers unsupported assistant replies and asserts dead-end run links stay hidden.
- `frontend/src/components/chat-shell/chat-shell.tsx` - Threads the new routing guidance fields from the server action into persisted chat UI state.
- `frontend/src/lib/analysis-examples.ts` - Replaces stale examples with supported deterioration and relative-language prompts.
- `frontend/src/components/analysis/analysis-composer-fields.tsx` - Aligns composer hint text with the supported deterministic routing surface.

## Decisions Made

- Use the preview contract as the front-end routing boundary so chat can stop unsupported requests before creating a run row.
- Keep unsupported guidance inside the chat transcript rather than redirecting users to a failed run page, because the milestone goal is to keep routing feedback in the conversation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Propagated routing guidance through `chat-shell` state**
- **Found during:** Task 2 (Render rewrite suggestions inline and align product examples with the supported routing surface)
- **Issue:** `chat-message-list` could render the new `rewriteSuggestions` and `routingReason` fields, but `chat-shell` was not yet forwarding those fields from the action reply into the assistant message state.
- **Fix:** Updated `frontend/src/components/chat-shell/chat-shell.tsx` to carry `rewriteSuggestions` and `routingReason` through the optimistic message append flow.
- **Files modified:** `frontend/src/components/chat-shell/chat-shell.tsx`
- **Verification:** `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx`
- **Committed in:** `3693c7e`

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** The fix stayed within the planned chat integration scope and was required for the new unsupported-guidance contract to actually reach the UI.

## Issues Encountered

None beyond the expected RED-phase test failures and the chat-shell propagation fix above.

## User Setup Required

None.

## Next Phase Readiness

- Phase 14 can now rely on chat as the place where routing succeeds or fails, which is the right substrate for delivering completed run answers directly into the conversation.
- The unsupported path is no longer a dead end, so future chat-native answer work can assume a cleaner conversation model with deterministic guidance already attached to the message stream.

## Self-Check: PASS

- `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-message-list.test.tsx src/components/chat-shell/chat-shell.test.tsx`
- `cd frontend && npm run build`

---
*Phase: 13-analyst-prompt-routing*
*Completed: 2026-04-18*
