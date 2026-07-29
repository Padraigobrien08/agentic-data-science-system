# Product

## Register

product

## Users

Operators and analysts who run SEC/EDGAR financial analysis and need results they can trust without ambiguity — traceable, isolated, inspectable runs rather than a black-box model answer. They work in a focused, evaluative mindset: asking a company- or peer-level question, reading the answer, then verifying the evidence behind it.

A second audience is **demo visitors** evaluating the product with no account (guest mode). Their context is a first impression: they need to reach a real analysis in one click and immediately understand what the product does.

## Product Purpose

A chat-first, evidence-first analysis platform over SEC EDGAR data. A user asks a company-level or peer-relative financial question in plain language; a deterministic numerical pipeline runs; the product returns a narrative answer with a confidence read, inline chart evidence, and a path into the underlying artifacts and run trace.

Success is a run the user trusts: every answer sits on persisted, auditable state (runs, steps, artifacts, critic/report phases), the numerical core stays deterministic and inspectable, and the interface never implies more certainty than the evidence supports. The chat is a product surface over that auditable machinery, not an unlogged transcript.

## Brand Personality

Precise, trustworthy, calm. Quiet, exact, auditable — the answer earns trust by showing its work, not by asserting confidence. Voice is specific and literal: name the metric and the finding, surface what weakens the claim, avoid marketing cadence. The interface recedes so the analysis is the hero; low chrome, neutral ground, no decoration competing with the content.

## Anti-references

- **AI-slop warmth** — cream/sand body backgrounds, glassmorphism, serif display faces, soft gradient glow. (The warm/editorial direction explicitly rejected during design; it read as generic and undermined the "precise/technical" trust signal.)
- **Generic SaaS** — the hero-metric template (big number + small label + gradient), identical icon-card grids, gradient heroes, a tracked-uppercase eyebrow above every section.
- **Cluttered enterprise dashboard** — dense competing chrome, low-hierarchy data dumps, everything visible at once. Density without hierarchy is the opposite of the "calm" goal.

## Design Principles

- **Show your work.** Trust is earned by inspectability, not claimed. Every answer traces to persisted runs, artifacts, and evidence; the "View trace / Evidence / Critic" paths are first-class, not buried.
- **Deterministic core, honest surface.** The numbers come from a deterministic pipeline. The UI never implies more certainty than the evidence supports — confidence reads, blocking caveats, and an explicit "what weakens the claim" are part of the answer, not fine print.
- **Quiet confidence.** Neutral zinc ground, restrained accent, one job per screen. The content is the hero; the interface should read as considered and get out of the way.
- **Frictionless entry.** A visitor can try a real analysis with no sign-up (guest demo). The first screen invites a concrete question and offers real starting points, not a login wall.
- **One system across surfaces.** Chat, runs, trace, and artifacts share a single visual language. Leaving the chat to inspect evidence should feel like the same product, not a different app.

## Accessibility & Inclusion

WCAG 2.1 AA. Body text ≥4.5:1 against its ground (including placeholder text); large/label text ≥3:1. Every animation has a `prefers-reduced-motion` alternative. Full keyboard navigation with a visible focus state on every interactive element. Semantic status color (confidence good/medium/bad, caveat warning/info) must remain distinguishable by more than hue and must clear contrast on the dark ground.
