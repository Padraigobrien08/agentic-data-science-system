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

An agent that investigates a dataset adaptively, and traces every claim back to the
deterministic computation behind it. No number in a trace comes from a language model.

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

- `agentic-ai`
- `llm`
- `mcp`
- `evaluation`
- `observability`
- `data-science`
- `edgar`
- `sec`
- `fastapi`
- `nextjs`
- `python`
- `postgres`

`agentic-ai`, `llm`, `evaluation` and `mcp` lead, because the reusable part is the loop; the
EDGAR topics are there for the dataset, not the architecture. The previous list opened with
`edgar`/`sec`/`financial-analysis`, which sold this as a fintech product.

## License

MIT — see [`LICENSE`](../LICENSE). Chosen for maximum reuse with minimal friction; the
alternative considered was Apache-2.0, for its explicit patent grant.
