# GitHub Listing Notes

The GitHub-facing settings for this repository.

## Repository Name

`auditable-agent-loop`

A descriptor rather than a coined name, deliberately. This is a portfolio project, so the name's
job is to let someone scanning a list of repositories understand what it is without clicking: it
is an agent, it runs a loop, and the loop is auditable. The app reads the same name from
[`frontend/src/lib/brand.ts`](../frontend/src/lib/brand.ts).

Previously `agentic-data-science-system` — a category rather than this project, leading with the
one word in it carrying the least information.

## Description

**Applied.** `gh repo view --json description` should match this exactly.

> An agent that investigates a dataset adaptively, and traces every claim back to the
> deterministic computation behind it. No number in a trace comes from a language model.

Replaces "End-to-end agentic data-science system: LLM planning + MCP tool execution over
deterministic analytics, with full traceability and evaluation." That version led with the
architecture rather than what the thing does, and claimed "full traceability" — the kind of
unbacked superlative this project's README now avoids on principle.

## Shorter Alternative

Adaptive investigation loop over tabular data, with an audit trail from any claim down to the
rows it came from.

## Pinned-Repos Blurb

An adaptive investigation loop that proposes competing explanations, tests each against
deterministic analysis, and records why it stopped. Every claim links to evidence, every evidence
record links to the experiment that computed it, and the model calls are audited on the same
footing — prompt, response, tokens and cost per phase. SEC EDGAR is the flagship dataset, but
EDGAR is an adapter, not the architecture.

## Topics

These are **applied**, not suggested — `gh repo view --json repositoryTopics` should match this
list exactly. GitHub sorts them alphabetically in its own UI.

What the loop is: `agentic-ai` · `ai-agents` · `llm` · `llm-orchestration` · `mcp` ·
`evaluation` · `explainable-ai` · `observability` · `data-science`

The stack: `fastapi` · `nextjs` · `python` · `typescript` · `postgresql`

The dataset: `edgar` · `sec`

The reasoning terms lead because the reusable part is the loop; EDGAR is there for the dataset,
not the architecture. Dropped from the earlier list: `financial-analysis` (sold this as a fintech
product), `microservices` (it is an API, a worker and a web app — not that), `orchestration`
(redundant beside `llm-orchestration`), and `artifact-management`, `async-processing`,
`prompt-engineering`, `benchmarking` as too vague to aid discovery. `mcp` was missing entirely,
which is the one term a reader looking for this kind of project is most likely to search.

`postgresql`, not `postgres` — GitHub treats the former as canonical and has a topic page for it.

## License

MIT — see [`LICENSE`](../LICENSE). Chosen for maximum reuse with minimal friction; the
alternative considered was Apache-2.0, for its explicit patent grant.
