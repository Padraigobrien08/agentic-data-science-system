---
target: frontend/src/components/chat-shell
total_score: 33
p0_count: 0
p1_count: 0
timestamp: 2026-07-29T09-46-46Z
slug: frontend-src-components-chat-shell
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Live per-phase pipeline progress (spinner→check→fail) from committed run state. Unchanged, still excellent. |
| 2 | Match System / Real World | 3 | Plain-language report + Strong/Moderate/Weak land; "Technical status" still surfaces raw orchestrationStatus. |
| 3 | User Control and Freedom | 3 | Delete is now an inline two-step confirm (up from native dialog). Honest gap unchanged: Stop halts the wait, not the server run. |
| 4 | Consistency and Standards | 4 | Both anchors of the prior 3 are fixed: banner is on-token and inverts; radii collapsed to a 4-step scale (pill/card/control/chip). Residual: focus-outline coverage partial, a few eyebrow labels remain. |
| 5 | Error Prevention | 4 | The cited weak link (native window.confirm) is gone; destructive delete now has a styled two-step confirm. New-chat still disabled without tickers. |
| 6 | Recognition Rather Than Recall | 3 | Starter prompts, visible scope chips, labeled icons, durable history. Unchanged. |
| 7 | Flexibility and Efficiency | 3 | Enter / Shift+Enter / Escape / prefill. Still no command palette or new-chat shortcut. |
| 8 | Aesthetic and Minimalist Design | 4 | Always-on delivery banner is now degraded-only (the cited noise is gone); calmer heading typography. Residual eyebrow labels on starter/skeleton frames. |
| 9 | Error Recovery | 3 | Clear error thesis + "open trace, retry narrower"; inline send errors. Error text now also clears AA on dark. |
| 10 | Help and Documentation | 2 | Empty state + starter prompts teach; no contextual help beyond that. Thin for a no-account demo. Unchanged. |
| **Total** | | **33/40** | **Good — solid foundation, weak areas remain** |

## Anti-Patterns Verdict

**LLM assessment:** Still does not read as AI-generated. The deliberate zinc/Geist product register holds, and the trust-first content model is specific to this product. Clears every absolute ban — no gradient text, side-stripes, decorative glass, hero-metric template, or identical card grid.

The one slop-adjacent tell from the baseline (uppercase-tracked kicker repeated as every heading) is **materially reduced** on the answer surface: the three narrative headers are now real sentence-case `<h3>`s, the confidence-popover section titles and "Visual evidence" are de-eyebrowed, and tracked-caps is reserved for the disclosure toggles. It is **not eliminated across the whole directory** — the starter-prompt cards and the assistant loading skeleton still carry the tracked-caps label grammar.

**Deterministic scan:** `detect.mjs` over `frontend/src/components/chat-shell` returned `[]` — zero findings (exit 0).

**Visual overlays:** Not available — no dev server with real chat state is running and the local-file browser path did not render under the sandbox CSP. The verdict rests on source review + the clean scan; the color findings were verified numerically (all status inks composited against their real grounds clear 4.5:1; most clear 7:1+), not observed in a rendered dark viewport.

## What's Working

1. **The color system now actually inverts.** The composer banner, confidence pills, caveat badges, and error text all run through `--status-*` tokens that flip in the dark media block. This closes both the P1 (light-fixed banner) and the P2 (sub-AA status inks) findings — and it fixed a latent bug: the surface uses `darkMode: "class"` with no `.dark` class, so the prior `dark:` utilities were dead code that never inverted.
2. **Radius reads as a system.** Eight bespoke radii collapsed to `pill / card / control / chip`; the shadcn `lg/md/sm` scale is untouched, so nothing app-wide drifted.
3. **Live phase progress + honesty architecture, still intact.** The trust model (per-step progress, supports/weakens/limits, graceful partial/error/no-data) survived the restyle unchanged.

## Priority Issues

**[P2] Eyebrow reduction stops at the answer card.** `chat-message-list.tsx:35,134` (starter-prompt cards) and `assistant-structured-frame.tsx:26,41` (loading skeleton: "Conclusion", "Goal") still use the `uppercase tracking-[0.16em]` kicker. The answer surface reads calm; the surrounding chat frame still carries the AI-grammar label style. Fix: sentence-case these or fold them into the card structure, reserving tracked-caps for the one toggle role established on the answer card. → `/impeccable typeset`

**[P2] Focus-visible coverage is partial.** The polish pass added the accent focus outline to the composer send button, sidebar buttons, and answer-surface triggers, but the **starter-prompt cards** (`chat-message-list.tsx:28`) and the **scope Edit / Save buttons** (`chat-shell.tsx:264,284`) are hand-rolled buttons with no `focus-visible` outline. Keyboard users get an inconsistent focus affordance across the same surface. → `/impeccable audit`

**[P2] Stop ends the wait, not the run.** Unchanged from baseline. "Stop" halts client polling, but the server run finishes and lands in history later, with no signal to the user that it is still executing. Fix: a "still running in the background" note on Stop. → `/impeccable harden`

**[P3] "Technical status" leaks system language.** The one spot where raw `orchestrationStatus` and system vocabulary surface on an otherwise plain-language surface. Fix: relabel to user language ("What the system did" / "Run details") and/or humanize the status string. → `/impeccable clarify`

**[P3] One stray radius escaped the scale.** `assistant-structured-frame.tsx:20` uses `rounded-bl-md`, a directional radius the sweep didn't catch. Map it to the new scale (`rounded-bl-[…]` off `control`) or accept it as an intentional chat-bubble tail. → `/impeccable polish`

## Persona Red Flags

- **Sam (a11y):** Big win — status color now clears AA on dark, and primary controls have visible focus outlines. Remaining: starter-prompt cards and scope Edit/Save buttons still lack a visible focus ring; the `role="status"` degraded banner now announces correctly.
- **Alex (power user):** Enter/Escape good; delete no longer drops into an OS dialog. Still no command palette or new-chat keyboard shortcut — the accelerator layer is still thin.
- **Riley (stress tester):** empty/partial/error/no-data all handled. Edge unchanged: "Stop" leaves the run executing server-side; it reappears in history with no "still running" cue.

## Minor Observations

- `foreground/95` and `/80` opacities still dilute tokens on the narrative body; a dedicated de-emphasis token would be cleaner than an opacity modifier.
- The scope header "Scope" prefix label is uppercase-tracked but reads as an acceptable single field label, not an eyebrow.
- Help/Documentation (score 2) is the lowest heuristic and untouched this pass; a no-account demo could teach more at the point of need.
