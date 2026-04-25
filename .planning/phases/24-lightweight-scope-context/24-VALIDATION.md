# Phase 24 Validation

## Commands

- `cd frontend && npm run test -- src/actions/runs.test.ts src/components/chat-shell/chat-composer.test.tsx src/components/chat-shell/chat-shell.test.tsx`
- `cd frontend && npm run build`

## Must Hold True

- Scope reads as quiet chat context in the shell.
- Scope editing stays inline and clearly affects future prompts.
- Chat runtime wording no longer uses workspace-first copy.
