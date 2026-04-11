# Artifact metadata and content delivery

The FastAPI app exposes registered **artifact rows** (DB metadata) separately from **stored bytes** (object storage). Clients use the artifact UUID in every URL path segment below.

**Authentication:** all `/v1/artifacts/*` routes require `Authorization: Bearer <access_token>` (see [`docs/auth-api.md`](auth-api.md)). Cross-tenant artifact IDs return **404** (not 403).

Base path: **`/v1/artifacts`**.

## Metadata: `GET /v1/artifacts/{artifact_id}`

Returns the artifact record (id, `role_key`, `kind`, `mime_type`, `byte_size`, `content_sha256`, `storage_uri`, lineage ids, timestamps, optional `meta_json`).

| Query | Default | Meaning |
|-------|---------|---------|
| `include_meta` | `false` | When `true`, includes `meta_json` (may be large). |

**404** if the row does not exist.

JSON field names are **snake_case** (Pydantic / OpenAPI).

## Content: `GET /v1/artifacts/{artifact_id}/content`

Streams the raw object bytes from storage via `open_reader` (e.g. `local:` URIs). Responses do not embed filesystem paths; use this route (or the preview route) instead of interpreting `storage_uri` in clients.

| Query | Default | Meaning |
|-------|---------|---------|
| `disposition` | `auto` | `auto`: inline for obvious text/JSON MIME types, otherwise attachment. `inline` / `attachment` force browser hint. |

Typical headers:

- `Content-Type` — from artifact `mime_type`, or `application/octet-stream` if unset.
- `Content-Disposition` — `inline` or `attachment` with an ASCII-safe `filename` derived from `role_key` and MIME/kind (see `artifact_content_filename`).
- `Content-Length` — when `byte_size` is known and non-negative.
- `ETag` — content SHA-256 when present.
- `Cache-Control: private, no-cache`, `X-Content-Type-Options: nosniff`.

**404** — unknown artifact, or blob missing in storage. **502** — unsupported URI scheme, invalid key, or I/O errors (generic `detail` strings; no internal paths in JSON).

## Preview: `GET /v1/artifacts/{artifact_id}/preview`

Returns JSON **`ArtifactPreviewResponse`**: bounded UTF-8 text for UI preview (not a second download API).

| Field | Meaning |
|-------|---------|
| `format` | `json` if the payload was valid JSON and was pretty-printed; else `text`. |
| `text` | UTF-8 string (replacement chars on decode issues). **Empty string** for zero-byte objects. |
| `truncated` | `true` if the object is larger than the server preview cap (~512 KiB read). |
| `mime_type` | From metadata (may be `null`). |
| `total_bytes` | Declared `byte_size` when known. |
| `json_valid` | When `format` is `json`, `true`; if MIME/kind suggest JSON but parsing fails, `false` and `format` stays `text`. |

**415** — preview is not offered for this artifact; use **`/content`** to fetch bytes.

**404** / **502** — same classes of errors as content (missing blob, storage misconfiguration, read failure).

## Previewable artifact types

Eligibility is implemented in `backend/services/artifact_delivery.py` (`artifact_previewable`):

1. If **`mime_type` is non-empty** (after trim, case-insensitive):
   - **Prefix `text/`** — previewable (includes `text/plain`, `text/markdown`, `text/csv`, etc.).
   - **Exact types** — `application/json`, `application/jsonl`, `application/x-ndjson`.
   - Any other explicit MIME (e.g. `application/pdf`, `application/octet-stream`) — **not** previewable → **415** on `/preview`.

2. If **`mime_type` is empty or whitespace** — kind fallback: **`document`**, **`json`**, or **`tabular`** are treated as previewable; other kinds are not.

## Frontend proxy (Next.js)

The web app calls the backend only from the server (`API_URL`). Browser access uses same-origin routes:

- `GET /api/artifacts/{artifact_id}/preview`
- `GET /api/artifacts/{artifact_id}/content?disposition=…`

These forward to the backend routes above and preserve status, JSON errors, and streaming headers where applicable.
