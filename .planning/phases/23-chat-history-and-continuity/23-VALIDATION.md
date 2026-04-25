# Phase 23 Validation

## Commands

- `cd frontend && npm run test -- src/lib/chat-run-history.test.ts src/components/chat-shell/chat-shell.test.tsx`
- `cd frontend && npm run build`

## Must Hold True

- The history rail is framed as prior answers in the chat.
- History items use meaningful answer-forward labels.
- Opening history keeps the user in the chat transcript instead of forcing a trace jump.
