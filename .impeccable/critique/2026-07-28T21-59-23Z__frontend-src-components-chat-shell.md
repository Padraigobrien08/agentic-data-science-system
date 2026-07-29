---
target: chat surface (frontend/src/components/chat-shell)
total_score: 30
p0_count: 0
p1_count: 1
timestamp: 2026-07-28T21-59-23Z
slug: frontend-src-components-chat-shell
---
## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 4 | Real per-phase pipeline progress (spinner → check → fail), live headline, polled from committed steps. Genuinely excellent. |
| 2 | Match System / Real World | 3 | Plain-language report + Strong/Moderate/Weak labels land; raw `orchestrationStatus` string still surfaced under "Technical status". |
| 3 | User Control and Freedom | 3 | Stop + Escape, new chat, delete-with-confirm, edit scope. Honest gap: Stop halts the *wait*, not the server run. No undo on delete. |
| 4 | Consistency and Standards | 3 | Zinc system now spans chat + app-skin, but the composer status banner is off-token and light-fixed, and radii sprawl (8+ bespoke values). |
| 5 | Error Prevention | 3 | New-chat disabled with no tickers; destructive delete confirmed. Native `window.confirm` is the weak link. |
| 6 | Recognition Rather Than Recall | 3 | Starter prompts, visible scope chips, labeled icons, durable history. Solid. |
| 7 | Flexibility and Efficiency | 3 | Enter-to-send, Shift+Enter, Escape-to-stop, prefill prompts. No command palette / new-chat shortcut. |
| 8 | Aesthetic and Minimalist Design | 3 | Calm, low-chrome, content-first. The always-on background-delivery banner adds noise when it isn't sync_only. |
| 9 | Error Recovery | 3 | Clear error thesis + "open trace, retry with narrower wording"; send errors shown inline. Plain language. |
| 10 | Help and Documentation | 2 | Empty state + starter prompts teach; no contextual help beyond that. Thin for a no-account demo audience. |
| **Total** | | **30/40** | **Good — solid foundation, address the weak areas** |

## Anti-Patterns Verdict

**LLM assessment:** This does not read as AI-generated. It commits to the Vercel-zinc/Geist template look deliberately (product register: earned familiarity is a feature, not a tell), and the trust-first content model — a confidence read, a "what weakens the claim" section, inline evidence, a path to the trace — is specific to this product, not generic scaffolding. It clears every absolute ban: no gradient text, no side-stripes, no decorative glass, no hero-metric template, no identical card grid.

The one slop-adjacent tell is the **uppercase-tracked micro-label used as a section kicker, 10 times across the answer surface** ("What's happening / Why we think that / What weakens the claim", "Supporting evidence", "Technical status", "Coverage limits"). One deliberate label role is voice; the same tracked-caps treatment on every section heading is the eyebrow-on-every-section grammar the brief explicitly rejects under "Generic SaaS".

**Deterministic scan:** `detect.mjs` over `frontend/src/components/chat-shell` returned `[]` — zero findings. Clean.

**Visual overlays:** Not available. This is a background job with no browser automation, so no live overlay was injected and no page-rendered evidence was collected. The verdict rests on source review plus the clean deterministic scan; the color findings below are computed from the token values, not observed in a rendered dark viewport, so eyeball them.

## Overall Impression

This is a calm, credible analysis surface that mostly gets out of the way of the answer — exactly the brief. The progress model is the standout: a chat that shows real pipeline phases instead of a fake typing dot is a genuine trust signal. What's holding it at "good" rather than "excellent" is a handful of consistency leaks that betray the single-system goal: one banner that ignores the token layer and won't survive dark mode, a radius vocabulary with no scale, and a typographic tic that repeats a banned pattern. None are hard to fix; all are visible.

Single biggest opportunity: make the color + type system airtight so "one system across surfaces" is true at the pixel level, not just structurally.

## What's Working

1. **Live phase progress (`chat-run-progress.tsx`).** Spinner → check → fail per pipeline step, polled from committed run state, with a `motion-safe:` spinner. This is the trust model made visible and it's the best thing on the surface.
2. **The answer card's honesty architecture.** Confidence pill with a "what supports / what weakens / coverage limits" popover, a dedicated "What weakens the claim" narrative section, and a graceful partial/error/no-data path. This is precisely the "never imply more certainty than the evidence supports" principle, built in.
3. **Committed, deliberate skin.** Zinc + Geist, low chrome, neutral ground, restrained single accent. It reads as considered, and it now extends to the app-skin routes so leaving chat for the trace stays one product.

## Priority Issues

**[P1] The composer background-delivery banner breaks the token system and dark mode.**
- **Why it matters:** `chat-composer.tsx:87-90` hardcodes `bg-emerald-50 text-emerald-900` (and amber/blue variants). These are light-fixed Tailwind palette values that never invert. On the zinc dark ground (`--background:#09090b`) this renders as a bright near-white block — a jarring light card floating in a dark composer, and the only element on the surface that ignores the semantic tokens. It directly violates "one system across surfaces" and the AA-on-dark requirement.
- **Fix:** Move to translucent tinted tokens like the confidence strip already uses: `border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300` (and amber/blue equivalents), or neutralize it to `--surface`/`--muted` since it's status, not a semantic alert. While there, drop the `uppercase tracking-[0.18em]` title.
- **Suggested command:** `/impeccable colorize` (or fold into `/impeccable harden`).

**[P2] Uppercase-tracked eyebrow repeated as every section heading (10 instances).**
- **Why it matters:** The narrative section headers, supporting-evidence label, technical-status summary, and explainer sub-heads all share the same `text-[11px] font-semibold uppercase tracking-[0.16em]` treatment. Repetition turns a label into scaffolding — the "tracked-uppercase eyebrow above every section" tell the brief calls out under Generic SaaS. It also flattens hierarchy: a section the reader must actually read ("What weakens the claim") looks identical to a fold-away micro-label ("Technical status").
- **Fix:** Give the three narrative section headers real heading treatment — sentence case, medium weight, `--foreground` at a step above body — and reserve the tracked-caps micro-label for one role only (e.g. the collapsed disclosure toggles).
- **Suggested command:** `/impeccable typeset`.

**[P2] Semantic status colors need an AA pass on the dark ground.**
- **Why it matters:** Confidence tones use `text-emerald-600 / amber-600 / rose-600` on a 10% tint, and `caveat-badge-group.tsx:11` uses `text-blue-500`. Against the dark surface (`#18181b`), `-600` text and especially `blue-500` (~3.7:1) fall below the 4.5:1 body-text bar the brief mandates. The label text means these aren't *hue-only*, which is good — but they're not yet contrast-safe on dark.
- **Fix:** Add `dark:text-emerald-400 / amber-400 / rose-400 / blue-400` variants (the 400 shades clear 4.5:1 on zinc-900) and verify each pairing.
- **Suggested command:** `/impeccable audit`.

**[P2] Border-radius vocabulary has no scale.**
- **Why it matters:** Across the surface: `rounded-full`, `rounded-[1.5rem]`, `rounded-[1.4rem]`, `rounded-[1.15rem]`, `rounded-2xl`, `rounded-xl`, `rounded-lg`, `rounded-md`. Eight bespoke radii with no system reads as accreted rather than designed, and subtly undercuts the "considered" goal.
- **Fix:** Collapse to a 3-4 step radius scale (pill / card / control / chip) as tokens or Tailwind theme values, and map every component to it.
- **Suggested command:** `/impeccable extract` (tokenize) then `/impeccable polish`.

**[P3] Native `window.confirm` for chat deletion.**
- **Why it matters:** The delete flow (`chat-sidebar.tsx:115`) drops out of the zinc system into an OS dialog — an abrupt tonal break in an otherwise calm surface, and unstyleable.
- **Fix:** Inline confirm (two-step button that morphs to "Confirm delete?") or a styled dialog consistent with the skin.
- **Suggested command:** `/impeccable harden`.

## Persona Red Flags

**Alex (Power User):** Enter sends and Escape stops — good. But there's no command palette or new-chat keyboard shortcut, so starting a fresh thread is a mouse trip to the sidebar. Delete routes through a native confirm (an extra modal dismissal). Nothing blocking, but the "accelerator" layer is thin for someone running many analyses.

**Sam (Accessibility-Dependent):** The `motion-safe:` spinner and aria-labels on icon buttons are right. Risks: the confidence/caveat status text at `-500/-600` on dark likely misses 4.5:1 (P2 above); the composer status banner conveys tone by color block; and I could not verify visible focus rings on the composer, send button, and sidebar links without a rendered page — check that every interactive element has a visible focus state on the zinc ground.

**Riley (Stress Tester):** The empty, partial, error, and no-data states are all handled with specific copy — strong. The honest edge: "Stop" ends the wait but the run keeps executing server-side and its answer later lands in history. That's defensible and documented, but a returning user may be surprised by an answer to a question they thought they cancelled. Consider a one-line "still running in the background" note when Stop is pressed.

## Minor Observations

- The always-on background-delivery banner is chrome the analyst didn't ask for; consider showing it only when degraded.
- `text-[var(--foreground)]/95` and `/80` border opacities dilute tokens slightly; prefer a dedicated token over per-use opacity so dark mode stays predictable.
- "Technical status" surfaces a raw orchestration string — fine as a fold-away, but it's the one spot where system language leaks into a plain-language surface.

## Questions to Consider

- If the confidence read is the trust anchor, should it be the most contrast-committed color on the card rather than a soft 10% tint?
- Does the background-delivery banner earn permanent residence in the composer, or is it status that belongs in a quieter place?
- What would the answer card look like if exactly one element used tracked-caps, and everything else earned hierarchy through weight and size?
