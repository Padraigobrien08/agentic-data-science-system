# Demo script — the five-minute path

The showcase narrative for a hosted reviewer. Written as what the visitor *sees*, in order,
with the claim each step is evidence for. Doubles as the brief for the README rewrite.

Audience: a technical reviewer with no account, no context, and little patience.
Direction and tiers: [`decisions/2026-08-11-showcase-direction.md`](./decisions/2026-08-11-showcase-direction.md).

---

## The one-sentence claim

*An agent that investigates a dataset adaptively, and can show you every step of its reasoning
back to the number it came from.*

Two halves. The demo must land both — adaptive reasoning is common, **auditable** adaptive
reasoning is the differentiator. If a reviewer leaves believing only the first half, the demo
has failed at exactly the thing the architecture was built for.

---

## Minute 0–1 · Landing: a finished investigation, not an empty box

The visitor arrives on a **completed investigation**, not a chat prompt. An empty input asks
them to do work before they have any reason to; a finished trace asks them only to read.

On screen: the goal in plain language, the hypotheses it generated, their final statuses, and
the conclusion with evidence links.

> **Claim:** this system produces structured, inspectable output — not a paragraph of prose.

Design note: the hypothesis statuses must be visible without scrolling. `supported` /
`weakened` / `rejected` / `inconclusive` sitting side by side is the fastest possible signal
that this is not a chatbot wrapper.

## Minute 1–2 · The reasoning is genuinely adaptive

Walk the recorded EDGAR run's timeline: the loop picked an experiment, got a result that
**contradicted** the working hypothesis, and changed course — a follow-up experiment it would
not have run had the first result gone the other way.

> **Claim:** the experiment sequence is a function of intermediate results, not a fixed script.

This is the load-bearing minute. A fixed pipeline can produce a nice report; only an adaptive
loop produces a *branch*. Make the branch point explicit — annotate it in the recorded run if
the UI does not surface it on its own.

## Minute 2–3 · It argues against itself, and it can say "I don't know"

Two beats, in this order:

1. **The critic challenged the finding** before it was concluded — a competing explanation
   raised, and either dismissed with evidence or promoted into its own hypothesis.
2. **The termination reason is typed and honest** — `sufficient_evidence` vs.
   `insufficient_evidence`, surfaced as a first-class outcome rather than buried.

> **Claim:** failure and uncertainty are valid outputs. The system does not manufacture
> confidence it has not earned.

If the recorded run terminated `insufficient_evidence`, **lead with that**. Counter-intuitively
it is the stronger demo: nearly every AI product on the market will confidently answer a
question it cannot answer, and showing the opposite is instantly legible to a technical
audience.

## Minute 3–4 · Every claim traces to a number

The drill-down, in one continuous motion:

conclusion → evidence reference → the experiment that produced it → the tool call and its typed
envelope → the artifact → **the actual rows**.

> **Claim:** this is auditable in the strict sense. No step in the chain is "trust me."

Then the second half of the audit trail: the model calls. Prompt, response, token counts,
cost, latency, per phase (`GET /v1/runs/{id}/llm-usage`). The LLM's contribution is itself
logged as evidence.

Land the invariant out loud, because it is the architectural spine of the whole repository:

> **The LLM plans and interprets. Deterministic code computes.** No number in that trace was
> produced by a language model.

## Minute 4–5 · It is not a finance toy

Switch to the recorded **non-EDGAR CSV** investigation. Same loop, same evidence model, same
trace surfaces, an unrelated dataset.

> **Claim:** EDGAR is an adapter, not the architecture.

Close on the engineering, quickly and without dwelling — one screen, three lines:

- **Measured, not asserted.** An agency benchmark with tiered cases and committed baseline
  floors, plus a scoreboard the suite must keep discriminating against
  ([`docs/agent/agency-scoreboard.md`](./agent/agency-scoreboard.md)).
- **Observable.** ~45 Prometheus series including the agent loop itself, a 13-panel Grafana
  dashboard, and alert rules that fire on the agent doing *poor work* — sustained
  `insufficient_evidence`, runs hitting budget ceilings instead of concluding — not just on
  outages ([`docs/observability.md`](./observability.md)). Screenshots; the stack is local-only.
- **Reproducible.** Runs are resumable from typed persisted state; replay produces a
  conclusion-first verdict of `identical` / `same_conclusion` / `diverged`
  ([`docs/agent/replay-and-diff.md`](./agent/replay-and-diff.md)).

---

## What the visitor can do themselves

| Tier | Entry | What they get |
|---|---|---|
| **Replay** | no account | the two recorded investigations, fully explorable |
| **Guest** | one click | their own live EDGAR run on the deterministic chain, with a narrative answer and full trace |
| **Adaptive** | invite code | the real loop on their own question |

The guest tier matters more than it looks: it converts the demo from *a thing they read* into
*a thing they did*. Even on the deterministic chain, the run is theirs, isolated, and produces
the same trace surfaces they just watched.

Put the invite code in the README and on the CV.

---

## Anti-goals

Per `PRODUCT.md`'s anti-references, and one specific to this demo:

- **No feature tour.** Nobody was ever convinced by a capability list. One investigation,
  followed all the way down, beats twelve features named.
- **No hedging on the honest failure.** If the run concluded `insufficient_evidence`, that is
  the headline, not an apology.
- **No claiming the observability stack is hosted.** Screenshots, labelled as local. Overstating
  what is deployed is precisely the kind of thing this reviewer is checking for.
- **No re-rolling the recorded run until it flatters.** The recorded trace is a claim about
  typical behaviour. Cherry-picking it makes the demo a lie that a reviewer running the guest
  tier could catch in ninety seconds.
