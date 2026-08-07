# Public API Contract

The HTTP API is the platform's primary integration surface. The web app, the
[orchestration MCP server](../mcp-platform-server.md), and any external client all go through
it — there is no privileged back door, which is why the MCP server can be hosted safely.

**[`openapi.json`](openapi.json)** is the committed contract, generated from the running app.

```bash
python3 scripts/export-openapi.py          # regenerate after changing a route
python3 scripts/export-openapi.py --check  # CI: fail if the committed copy is stale
```

The artifact is committed rather than generated on demand so an API change is **visible in
code review**: adding a route, renaming a field, or changing a status code shows up as a diff
on the contract, not just inside a handler. CI enforces that it stays in step.

## Versioning

- All product endpoints live under **`/v1`**. Operational endpoints (`/health`, `/ready`,
  `/metrics`) sit outside it deliberately — they are infrastructure, not product API.
- Within `/v1`, changes are **additive**: new endpoints, new optional request fields, new
  response fields. Clients must tolerate unknown response fields.
- A breaking change (removing or renaming a field, changing a status code's meaning, making an
  optional field required) requires a new prefix, not a mutation of `/v1`.
- `info.version` in the schema tracks the application, not the contract. The prefix is the
  contract version.

## Authentication

Bearer JWT, obtained from `POST /v1/auth/login`:

```
Authorization: Bearer <access_token>
```

Two endpoint classes sit outside normal user auth:

| Class | Auth | Endpoints |
|---|---|---|
| Ops | `EDGAR_BACKEND_OPS_API_TOKEN` bearer | `/metrics`, `/v1/worker/health` |
| Bootstrap | `EDGAR_BACKEND_BOOTSTRAP_ADMIN_TOKEN` | `POST /v1/auth/bootstrap` |

## Error semantics

| Status | Meaning |
|---|---|
| `400` | Malformed request the server understood but cannot accept |
| `401` | Missing or invalid credentials |
| `403` | Authenticated, but the operation is disabled by configuration |
| `404` | The resource does not exist **or** is not yours |
| `409` | Valid request that conflicts with current state (e.g. engine disabled, bad status transition) |
| `415` | Unsupported media type (e.g. previewing a binary artifact) |
| `422` | Request failed schema validation (FastAPI's default shape) |
| `429` | Rate limited; `Retry-After` is set |

**`404` is deliberately ambiguous.** Ownership checks return `404` for both "missing" and
"not yours", so the API never reveals that a resource exists to someone who cannot read it.
Clients must not infer existence from a `404`, and integrations should relay it as-is rather
than translating it to "deleted".

## Conventions

- **IDs** are UUIDs. Artifact IDs are opaque: they never encode a storage path, so a client
  cannot derive one identifier from another.
- **Timestamps** are ISO-8601 UTC.
- **Lists** are paginated with `limit` / `offset` and bounded server-side.
- **Long-running work** is asynchronous. `POST /v1/runs` and `POST /v1/investigations` accept
  an enqueue option and return immediately; poll `GET /v1/runs/{id}/status`.

## Generating a client

The schema is standard OpenAPI 3.1, so any generator works without booting the stack:

```bash
npx @openapitools/openapi-generator-cli generate \
  -i docs/api/openapi.json -g typescript-fetch -o ./generated-client
```

Interactive docs are served at `/docs` and `/redoc` when the app is running.
