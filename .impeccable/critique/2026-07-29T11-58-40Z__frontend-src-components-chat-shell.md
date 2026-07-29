---
target: frontend/src/components/chat-shell
total_score: 36
p0_count: 0
p1_count: 0
timestamp: 2026-07-29T11-58-40Z
slug: frontend-src-components-chat-shell
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Live per-phase pipeline progress. Excellent. |
| 2 | Match System / Real World | 4 | Plain-language surface; "Run details" replaced the jargon label. |
| 3 | User Control and Freedom | 4 | Honest Stop notice; dismissable first-run hint; delete confirm; edit scope. |
| 4 | Consistency and Standards | 4 | `HelpHint` reuses the shared Popover; focus/radius/color tokens uniform surface-wide. |
| 5 | Error Prevention | 4 | Inline two-step delete confirm; disabled states; validation. |
| 6 | Recognition Rather Than Recall | 3 | Starters, scope chips, labeled icons, durable history. Recent runs/outcomes still only in the sidebar. |
| 7 | Flexibility and Efficiency | 3 | Enter / Shift+Enter / Escape / prefill. Still no command palette or new-chat shortcut. |
| 8 | Aesthetic and Minimalist Design | 4 | Degraded-only banner; eyebrows resolved; help is a 14px `?` + one dismissable hint, not clutter. |
| 9 | Error Recovery | 3 | Clear error thesis + "open trace, retry narrower"; no inline retry affordance. |
| 10 | Help and Documentation | 3 | Contextual `?` at Scope, a first-run "how this works" hint, and the confidence popover now deliver help at the point of use. No searchable help or shortcut reference yet. |
| **Total** | | **36/40** | **Excellent (bottom of band) — remaining gaps are feature-level** |

## Anti-Patterns Verdict

**LLM assessment:** Does not read as AI-generated. The eyebrow tell is fully resolved (tracked-caps only in reserved disclosure toggles). The new help affordances follow the point-of-use pattern rather than a forced tour or modal ceremony, which is the right register call for a trust-first analysis tool. Every absolute ban is clear.

**Deterministic scan:** `detect.mjs` over `frontend/src/components/chat-shell` returned `[]` — zero findings (exit 0).

**Visual overlays:** Not available — no dev server with real chat state is running and the local-file browser path did not render under the sandbox CSP. The verdict rests on source review + the clean scan; the new help affordances were verified via a static two-theme preview and the test suite, not a live viewport.

## What's Working

1. **Help lives at the point of use.** The Scope concept (the one genuinely opaque domain term) now has a contextual `?`, and a dismissable first-run hint teaches the ask → confidence → verify loop on the empty state. No tour, no modal, no nagging — persisted per browser and shown once. This is the lowest-heuristic lever, moved correctly.
2. **The system stayed coherent while growing.** `HelpHint` reuses the shared Popover, the hint uses the same `card` radius and focus outline as everything else; adding help didn't add a new vocabulary.
3. **Honest control + trust architecture, intact.** Live phase progress, the supports/weakens/limits confidence model, and the honest Stop notice all hold.

## Priority Issues

**[P2] Accelerator layer is the last real gap (Flexibility, score 3).** Enter / Shift+Enter / Escape exist, but there is still no command palette, no new-chat shortcut, and no keyboard path to switch threads. This is what separates the surface from a top-band Flexibility score and is the clearest remaining lever for power users. Fix: a new-chat shortcut and a minimal ⌘K palette over threads + starter prompts. → feature task (no direct impeccable command).

**[P3] Help can go one step further.** The point-of-use help is good, but there's no keyboard-shortcut reference and the confidence pill isn't signposted as help for a first-timer (it self-documents only once clicked). A small "?" or a shortcut cheatsheet would round it out. → `/impeccable onboard` (follow-up) / feature task.

**[P3] Recognition aids stay in the sidebar (score 3).** Recent runs and their outcomes aren't surfaced inline in the conversation flow, so switching context still leans on the sidebar. → `/impeccable layout` / feature task.

**[P3] No inline retry on error (Error Recovery, score 3).** The error state gives a clear thesis and "open trace, retry narrower" copy, but no one-tap retry with adjusted wording. → `/impeccable harden` (follow-up).

## Persona Red Flags

- **Alex (power user):** The remaining friction is entirely the accelerator layer — no command palette, no new-chat shortcut. Everything else (Enter/Escape/delete-confirm) is solid.
- **Jordan (first-timer):** Materially better this pass — the empty state now explains the model, and Scope has an in-place explanation. Remaining: the confidence pill only teaches once opened.
- **Sam (a11y):** Strong — contextual help is keyboard-reachable with the accent focus outline, the first-run hint is dismissable and announced via the `role="log"` region, status color clears AA on dark.

## Minor Observations

- The confidence popover, `HelpHint`, and evidence disclosure now form a consistent "click to learn more" family; a single shared affordance style (e.g. a subtle `?` everywhere help exists) would make that pattern legible at a glance.
- Flexibility (3) is now the single lowest-with-a-clear-fix heuristic; it needs keyboard-accelerator feature work, not another refinement pass.
- `foreground/95` and `/80` opacity modifiers still stand in for a dedicated de-emphasis token on the narrative body.
