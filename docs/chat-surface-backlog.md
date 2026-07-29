# Chat surface — follow-up backlog

Feature-level follow-ups left after the v1.6 chat-surface refinement (`/impeccable`
critique trend **30 → 33 → 35 → 36/40**, zero P0/P1). These four items are the
remaining path from the bottom of the "Excellent" band (36) toward 38+. They are
**product/feature work, not refinement passes** — a polish/typeset/colorize pass will
not move them — so they route through the normal GSD workflow rather than an
`/impeccable` command.

Surface: `frontend/src/components/chat-shell/`
Latest critique snapshot: `.impeccable/critique/2026-07-29T11-58-40Z__frontend-src-components-chat-shell.md`

---

## 1. Command palette + new-chat keyboard shortcut  · P2 · Flexibility (heuristic 7, 3/10)

**Problem.** The only accelerators are Enter / Shift+Enter / Escape / starter-prompt
prefill. There is no command palette, no new-chat shortcut, and no keyboard path to
switch threads. Power users (persona "Alex") hit this ceiling immediately; it is the
single clearest lever left on the surface.

**Approach.**
- A `⌘K` / `Ctrl+K` command palette over: existing threads (from `chatThreads`), the
  starter prompts (`ANALYSIS_EXAMPLES`), and core actions (new chat, edit scope).
- A dedicated new-chat shortcut (e.g. `⌘⇧O`) wired to the existing
  `newConversationAction` in `chat-sidebar.tsx`.
- Reuse the shared Radix primitives; render the palette in a portal/dialog so it
  escapes the sidebar stacking context.

**Acceptance.**
- Palette opens/closes by keyboard, is fully keyboard-navigable, traps focus, closes on
  Escape, and has a visible focus state consistent with the surface's accent outline.
- New-chat shortcut is discoverable (shown in the palette and/or a shortcut reference —
  see item 4) and disabled when scope has no tickers, matching the sidebar button.
- `prefers-reduced-motion` respected for any open/close transition.

**Files.** `chat-shell.tsx`, `chat-sidebar.tsx`, `@/lib/analysis-examples`.

---

## 2. Inline retry on error  · P3 · Error Recovery (heuristic 9, 3/10)

**Problem.** The error answer state gives a clear thesis ("This analysis didn't finish
cleanly.") and guidance ("open trace, retry narrower"), but there is no one-tap retry.
The user must retype or re-navigate to try again.

**Approach.**
- Add a "Retry" action on the error answer card that re-submits the originating goal
  (optionally pre-filled into the composer for narrowing) via the existing `onSend`
  path, reusing the request-id/finalize flow.
- Consider a "Retry with refreshed SEC data" variant that sets `refresh: true`.

**Acceptance.**
- Retry re-runs the same goal without retyping; the composer/goal is preserved.
- Button uses the established control styling + accent focus outline.
- No duplicate-run race: the in-flight guard (`activeRequestId`) still holds.

**Files.** `chat-run-answer-card.tsx` (error branch), `chat-shell.tsx` (`onSend`),
`@/actions/runs`.

---

## 3. Inline recent-runs surfacing  · P3 · Recognition (heuristic 6, 3/10)

**Problem.** Recent runs and their outcomes live only in the sidebar history. Switching
context back to a prior answer leans on recall of the sidebar list rather than a cue in
the conversation flow.

**Approach.**
- Surface a compact "recent runs" affordance inline (e.g. at the top of the thread or in
  the empty state for returning users) showing the last N runs with status + a one-line
  preview, linking to the persisted answer/trace.
- Reuse `ChatRecentRun` (already defined in `types.ts`) and the durable message/run
  history rather than new client state.

**Acceptance.**
- Recent runs are visible without opening the sidebar, each row keyboard-focusable and
  linking to the correct persisted answer.
- Respects the "calm / content-first" register — this is a light affordance, not a
  second dashboard.

**Files.** `chat-message-list.tsx` (empty/returning state), `types.ts` (`ChatRecentRun`),
history loading in the chat page route.

---

## 4. Keyboard-shortcut reference / help signposting  · P3 · Help & Documentation (heuristic 10, 3/10)

**Problem.** Point-of-use help now exists (Scope `?` via `HelpHint`, the first-run
"How this works" hint, the confidence popover), which lifted this heuristic from 2 to 3.
What is still missing: a keyboard-shortcut reference, and the confidence pill only teaches
once opened (it is not signposted as help for a first-timer).

**Approach.**
- A shortcut cheatsheet (e.g. `?` key opens it, or an entry in the command palette from
  item 1) listing Enter/Shift+Enter/Escape/new-chat/palette.
- Consider a subtle, consistent "help exists here" affordance so the confidence pill and
  other self-documenting controls read as learnable at a glance (the `HelpHint` `?` is a
  good candidate to standardize on).

**Acceptance.**
- A discoverable, keyboard-openable shortcut reference exists.
- The "click to learn more" family (confidence popover, `HelpHint`, evidence disclosure)
  shares one legible affordance style.

**Files.** new shortcut-reference component, `help-hint.tsx` (reuse), `confidence-strip.tsx`.

---

### Not in scope / already resolved this cycle
- Banner off-token + non-inverting dark mode — **fixed** (`--status-*` tokens).
- Radius sprawl — **fixed** (`pill/card/control/chip` scale).
- `window.confirm` delete — **fixed** (inline two-step confirm).
- Uppercase-eyebrow tell — **fixed** (sentence-case headings; tracked-caps reserved for toggles).
- Focus-visible coverage — **fixed** (accent outline on every hand-rolled control).
- Silent Stop — **fixed** (honest "may still finish in the background" system notice).
- "Technical status" jargon — **fixed** (relabeled "Run details").

### Known unrelated debt
- `frontend/src/actions/runs.test.ts` type staleness — **fixed** this cycle.
- `ChatAssistantMessage.deepDiveHref` / `.runsHref` in `types.ts` are now unused dead
  fields from the `runHref` rename (no readers; safe to delete in a cleanup).
