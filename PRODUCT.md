# Product

## Register

product

## Users

The **primary audience is a technical reviewer** evaluating the engineering — someone who arrives with no account, no context, and little patience, and who forms a judgement in under five minutes. They are not trying to analyse a company; they are trying to find out whether the reasoning is real and whether the claims hold up under a drill-down. See [`docs/demo-script.md`](docs/demo-script.md).

The **modelled end user** is an operator or analyst who needs results they can trust without ambiguity — traceable, isolated, inspectable runs rather than a black-box model answer. They ask a question, read the answer, then verify the evidence behind it. The product is designed for them; it is currently *shown* to reviewers.

Access is tiered by cost (see [`docs/decisions/2026-08-11-showcase-direction.md`](docs/decisions/2026-08-11-showcase-direction.md)): **replay** of recorded investigations with no account, a **guest** tier running the deterministic chain in one click, and an **adaptive** tier running the full agentic loop, unlocked by an invite code at registration.

## Product Purpose

An **auditable agentic analysis platform over tabular data**, with SEC EDGAR as the flagship dataset. A user states a goal in plain language; an investigation loop generates hypotheses, chooses experiments adaptively from intermediate results, updates evidence, challenges its own findings, and stops for an explicit typed reason. The product returns an evidence-linked conclusion with a confidence read, inline chart evidence, and a path from any claim down to the rows it came from.

The governing invariant: **the LLM plans and interprets; deterministic code computes.** No number in a trace is produced by a language model.

Success is a run the user trusts: every claim links to evidence, every experiment has typed inputs and outputs, every run is reproducible from persisted structured state, and the interface never implies more certainty than the evidence supports. Uncertainty and failure are first-class outputs — `insufficient_evidence` is a valid, honest answer, not a degraded one.

EDGAR is an adapter, not the architecture. The same loop, evidence model, and trace surfaces run over an arbitrary uploaded dataset.

## Brand Personality

Precise, trustworthy, calm. Quiet, exact, auditable — the answer earns trust by showing its work, not by asserting confidence. Voice is specific and literal: name the metric and the finding, surface what weakens the claim, avoid marketing cadence. The interface recedes so the analysis is the hero; low chrome, neutral ground, no decoration competing with the content.

## Anti-references

- **AI-slop warmth** — cream/sand body backgrounds, glassmorphism, serif display faces, soft gradient glow. (The warm/editorial direction explicitly rejected during design; it read as generic and undermined the "precise/technical" trust signal.)
- **Generic SaaS** — the hero-metric template (big number + small label + gradient), identical icon-card grids, gradient heroes, a tracked-uppercase eyebrow above every section.
- **Cluttered enterprise dashboard** — dense competing chrome, low-hierarchy data dumps, everything visible at once. Density without hierarchy is the opposite of the "calm" goal.

## Design Principles

- **Show your work.** Trust is earned by inspectability, not claimed. Every answer traces to persisted runs, artifacts, and evidence; the "View trace / Evidence / Critic" paths are first-class, not buried.
- **Deterministic core, honest surface.** The numbers come from deterministic code; the model selects and interprets. The UI never implies more certainty than the evidence supports — confidence reads, blocking caveats, and an explicit "what weakens the claim" are part of the answer, not fine print.
- **Uncertainty is an answer.** A run that stops on `insufficient_evidence` has succeeded at being honest. Typed termination reasons and `supported` / `weakened` / `rejected` / `inconclusive` hypothesis states are surfaced as outcomes, never buried as errors.
- **Quiet confidence.** Neutral zinc ground, restrained accent, one job per screen. The content is the hero; the interface should read as considered and get out of the way.
- **Frictionless entry.** A visitor reaches a real, finished investigation with no sign-up and no empty input box, and can run their own in one click. The first screen shows work already done, not a login wall.
- **One system across surfaces.** Chat, runs, trace, and artifacts share a single visual language. Leaving the chat to inspect evidence should feel like the same product, not a different app.

## Accessibility & Inclusion

WCAG 2.1 AA. Body text ≥4.5:1 against its ground (including placeholder text); large/label text ≥3:1. Every animation has a `prefers-reduced-motion` alternative. Full keyboard navigation with a visible focus state on every interactive element. Semantic status color (confidence good/medium/bad, caveat warning/info) must remain distinguishable by more than hue and must clear contrast on the dark ground.
