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

## Transports and the two trust models

The transports have genuinely different trust models, and conflating them is the main way a
hosted MCP server goes wrong.

### stdio — one user, launched as a subprocess

The MCP host starts the server for a single user. Their token comes from the environment.

```bash
EDGAR_MCP_TOKEN="$(curl -s -X POST http://127.0.0.1:8000/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"you@example.com","password":"..."}' | jq -r .access_token)" \
python -m backend.mcp
```

### streamable-http — hosted, many callers

```bash
python -m backend.mcp --transport streamable-http --host 127.0.0.1 --port 8765
```

Every request must carry its own `Authorization: Bearer <token>`, and the server acts strictly
as that caller. **`EDGAR_MCP_TOKEN` is deliberately ignored in this mode** (the server logs a
warning if it is set). If a request without credentials fell back to the environment token,
every anonymous caller would inherit the operator's access — so a request without a usable
header is refused instead.

Ownership then follows from the API: two callers hitting the same hosted server see only their
own investigations, because each call is made with their own token and the API's owner scoping
does the rest.

> **Deployment note.** The MCP handshake and tool *listing* are unauthenticated — they expose
> the tool schema, not user data, which is normal for MCP. Every tool *invocation* requires the
> caller's token. Bind to loopback (the default) and put a reverse proxy in front if you also
> want the endpoint itself closed to unauthenticated traffic.

| Variable | Default | Purpose |
|---|---|---|
| `EDGAR_MCP_API_URL` | `http://127.0.0.1:8000` | Base URL of the platform API |
| `EDGAR_MCP_TOKEN` | *(stdio only)* | Bearer token from `POST /v1/auth/login`; ignored over HTTP |
| `EDGAR_MCP_TIMEOUT` | `60` | Per-request timeout in seconds |
| `EDGAR_MCP_TRANSPORT` | `stdio` | Default transport (`--transport` overrides) |
| `EDGAR_MCP_HOST` | `127.0.0.1` | Bind address for HTTP transports |
| `EDGAR_MCP_PORT` | `8765` | Bind port for HTTP transports |

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

- No tool for replay/diff yet; `InvestigationReplayService` is service-level only.
- No rate limiting on the hosted endpoint; the API's own auth rate limiting does not cover
  tool invocations, which authenticate with an already-issued token.
