# Orchestration MCP Server

Exposes the **investigation platform** over MCP: commissioning an investigation, reading its
hypotheses and evidence, and fetching the artifacts behind them.

This is the counterpart to [`edgar_project/mcp/`](../edgar_project/mcp/README.md), which
exposes the deterministic EDGAR *computation*. Together they let an external agent both
compute over SEC data and reason over persisted, auditable runs.

| | `edgar_project.mcp` | `backend.mcp` |
|---|---|---|
| Exposes | Deterministic EDGAR tools | The investigation platform |
| Talks to | `src/` directly | The `/v1` API over HTTP |
| Auth | None (local process) | Bearer token, owner-scoped |

## Design: a client of the API, not a second implementation

Every tool is an HTTP call to `/v1`. That is deliberate — going through the API means each
call inherits its authentication, owner scoping, validation, and 404-for-unauthorized
semantics. **The MCP server grants no access the token does not already have**, and the same
server works against a local stack or a deployed instance without change.

The alternative (opening a database session directly) would have duplicated service logic and
bypassed ownership checks entirely.

## Running it

```bash
EDGAR_MCP_TOKEN="$(curl -s -X POST http://127.0.0.1:8000/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"..."}' | jq -r .access_token)" \
python -m backend.mcp
```

| Variable | Default | Purpose |
|---|---|---|
| `EDGAR_MCP_API_URL` | `http://127.0.0.1:8000` | Base URL of the platform API |
| `EDGAR_MCP_TOKEN` | *(required)* | Bearer token from `POST /v1/auth/login` |
| `EDGAR_MCP_TIMEOUT` | `60` | Per-request timeout in seconds |

Transport is stdio today. A streamable-HTTP transport, so the server can be hosted rather
than launched per-client, is the next increment.

## Tools

| Tool | Purpose |
|---|---|
| `start_investigation` | Commission an adaptive investigation over CSV or records and run it |
| `list_investigations` | List investigations visible to the token, newest first |
| `get_investigation` | Full state: hypotheses, evidence, experiments, decisions, conclusion |
| `get_conclusion` | Just the answer: conclusion, disposition, confidence, why it stopped |
| `list_hypotheses` | Hypotheses with status and confidence |
| `get_evidence` | Evidence, optionally filtered to one hypothesis |
| `get_run_status` | Poll an async investigation |
| `list_artifacts` | Artifacts a run produced |
| `get_artifact_preview` | Bounded text preview of one artifact |

`get_investigation` returns everything; `get_conclusion`, `list_hypotheses`, and
`get_evidence` exist because an agent asking "what were the hypotheses?" should not have to
pull an entire investigation into its context to find out. List responses are capped
(`MAX_LIST_LIMIT`) so a single call can never flood a context window.

## Resources

| URI | Content |
|---|---|
| `artifact://{artifact_id}` | The artifact's preview text |
| `investigation://{investigation_id}/conclusion` | The conclusion rendered as readable text |

Resources are the right fit for evidence an agent wants to *read* rather than call, so an
artifact can be attached to a conversation by URI.

## Response contract

Tools return the same `ToolResponseEnvelope` shape as the EDGAR server
(`status` / `message` / `data` / `artifacts` / `errors`), so a client sees one response shape
across both servers.

**Errors never cross the MCP boundary as exceptions.** An API failure becomes an error
envelope with a stable code and the originating HTTP status, so an agent gets something it can
reason about rather than a transport-level crash. A missing *or* unauthorized resource is
relayed as `http_status: 404` without speculating about which it was — the API's ownership
semantics pass through unchanged.

## Follow-ups

- Streamable-HTTP transport with bearer auth, so the server can be hosted (C2).
- No tool for replay/diff yet; `InvestigationReplayService` is service-level only.
