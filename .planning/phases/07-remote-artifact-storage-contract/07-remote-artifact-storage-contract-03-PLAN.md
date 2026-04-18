---
phase: 07-remote-artifact-storage-contract
plan: 03
type: execute
wave: 3
depends_on:
  - 07-01
  - 07-02
files_modified:
  - .env.example
  - docker-compose.yml
  - backend/api/routes/artifacts.py
  - tests/test_artifact_content_delivery.py
  - docs/local-stack.md
  - docs/artifact-delivery.md
autonomous: true
requirements:
  - STOR-01
  - OPS-02
must_haves:
  truths:
    - "Artifact metadata, content, and preview routes keep the same auth and response contract whether the blob is local or remote."
    - "Remote-backed route failures stay generic and never expose bucket names, object keys, or endpoint details."
    - "Operators can opt into remote storage through documented env vars and Compose pass-throughs without changing the local filesystem default."
  artifacts:
    - path: backend/api/routes/artifacts.py
      provides: "Route-level remote delivery semantics that stay auth-safe and opaque"
    - path: tests/test_artifact_content_delivery.py
      provides: "Route regressions for S3-backed metadata, content, preview, and no-leak failure behavior"
    - path: .env.example
      provides: "Optional remote-storage env surface for operators"
    - path: docker-compose.yml
      provides: "Compose pass-through for remote-storage configuration while keeping local disk as the default"
    - path: docs/local-stack.md
      provides: "Runbook for enabling the optional S3-compatible backend in the local stack"
    - path: docs/artifact-delivery.md
      provides: "Artifact contract docs that describe `s3:` locators as opaque and app-owned"
  key_links:
    - from: backend/api/routes/artifacts.py
      to: tests/test_artifact_content_delivery.py
      via: "route regressions prove local and remote artifacts share the same delivery semantics"
      pattern: "Storage backend is not configured for this artifact|Artifact content expired by retention policy|s3:"
    - from: .env.example
      to: docker-compose.yml
      via: "documented env vars are passed into the API and worker services without changing the local default"
      pattern: "EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET"
    - from: docs/artifact-delivery.md
      to: backend/api/routes/artifacts.py
      via: "docs describe the same auth-safe content and preview contract the route enforces"
      pattern: "storage_uri|/v1/artifacts/{artifact_id}/content|/v1/artifacts/{artifact_id}/preview"
---

<objective>
Finish the product-facing proof: auth-safe route behavior and truthful operator docs for remote-backed artifact storage.

Purpose: satisfy the delivery side of `STOR-01` and `OPS-02` by proving that S3-backed artifacts still use the same application-owned content path and opaque metadata contract.
Output: remote-backed artifact route regressions, optional env wiring for the local stack, and docs that explain the remote-storage contract without exposing provider details.
</objective>

<execution_context>
@/Users/padraigobrien/.codex/get-shit-done/workflows/execute-plan.md
@/Users/padraigobrien/.codex/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/REQUIREMENTS.md
@.planning/STATE.md
@.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
@.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
@.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
@.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-01-PLAN.md
@.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-02-PLAN.md
@backend/api/routes/artifacts.py
@tests/test_artifact_content_delivery.py
@.env.example
@docker-compose.yml
@docs/local-stack.md
@docs/artifact-delivery.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Prove artifact metadata, content, and preview routes stay stable for S3-backed blobs</name>
  <files>backend/api/routes/artifacts.py
tests/test_artifact_content_delivery.py</files>
  <read_first>.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
backend/api/routes/artifacts.py
tests/test_artifact_content_delivery.py
tests/test_artifact_storage_s3.py
docs/artifact-delivery.md</read_first>
  <behavior>
    - Per D-04 and D-06, `/v1/artifacts/{id}`, `/content`, and `/preview` keep the same auth boundary and route shape for remote-backed artifacts.
    - Per D-05 and D-06, metadata and error bodies do not expose bucket names, object keys, or endpoint details.
    - Per D-08, tombstoned remote artifacts still return `410` before any storage read, while untombstoned remote failures keep the existing generic `404` or `502` classes.
  </behavior>
  <action>Extend `tests/test_artifact_content_delivery.py` so the harness can run with S3-backed settings and a moto bucket in addition to the current local store. Add remote-backed regressions that: create an artifact through the service, call `GET /v1/artifacts/{id}` and assert the same artifact `id`, `role_key`, and a logical `storage_uri` starting with `s3:` that does not contain the configured bucket; fetch `/content` and `/preview` successfully through the existing routes; and force misconfigured or missing remote objects to assert the same generic `404` or `502` details without bucket or endpoint leakage. Update `backend/api/routes/artifacts.py` only as needed so content and preview use matching generic wording for unsupported or misconfigured remote storage and keep the tombstone short-circuit intact.</action>
  <acceptance_criteria>`tests/test_artifact_content_delivery.py` contains S3-backed harness or fixture coverage.
`tests/test_artifact_content_delivery.py` asserts `storage_uri` starts with `s3:`.
`tests/test_artifact_content_delivery.py` asserts the configured bucket string is absent from metadata or error payloads.
`tests/test_artifact_content_delivery.py` contains successful `/content` coverage for an S3-backed artifact.
`tests/test_artifact_content_delivery.py` contains successful `/preview` coverage for an S3-backed artifact.
`backend/api/routes/artifacts.py` still contains `Artifact content expired by retention policy`.
`backend/api/routes/artifacts.py` contains generic `502` handling for unsupported or misconfigured storage.
`python3 -m pytest tests/test_artifact_content_delivery.py tests/test_artifact_storage_s3.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_content_delivery.py tests/test_artifact_storage_s3.py -q --tb=short</automated>
  </verify>
  <done>Remote-backed artifacts now prove they share the same auth-safe metadata, content, and preview routes as local artifacts.</done>
</task>

<task type="auto">
  <name>Task 2: Document and wire optional remote-storage configuration without changing the local default</name>
  <files>.env.example
docker-compose.yml
docs/local-stack.md
docs/artifact-delivery.md</files>
  <read_first>.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
.env.example
docker-compose.yml
docs/local-stack.md
docs/artifact-delivery.md
backend/config/settings.py
backend/api/routes/artifacts.py</read_first>
  <behavior>
    - Local filesystem storage remains the documented default for the quick-start stack.
    - Operators can opt into the remote backend with explicit env vars instead of hidden code assumptions.
    - Docs make clear that `storage_uri` is a logical app-owned locator, not a client-side bucket or signed-URL contract.
  </behavior>
  <action>Update `.env.example` with commented optional vars for `EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND`, `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET`, `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_REGION`, `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_PREFIX`, `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ENDPOINT_URL`, `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ACCESS_KEY_ID`, `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_SECRET_ACCESS_KEY`, and `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_FORCE_PATH_STYLE`. Update `docker-compose.yml` so API and worker pass those vars through when set, while retaining the existing filesystem root and local default behavior. Update `docs/local-stack.md` with an operator section explaining how to keep the default local store or opt into an external S3-compatible endpoint, explicitly noting that this stack still does not add MinIO. Update `docs/artifact-delivery.md` so `storage_uri` examples include `s3:` alongside `local:`, explain that the locator is logical and opaque, and repeat that clients must use the application content or preview routes instead of treating the locator as a raw bucket or object identifier.</action>
  <acceptance_criteria>`.env.example` contains `EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND`.
`.env.example` contains `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET`.
`.env.example` contains `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ENDPOINT_URL`.
`.env.example` contains `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_FORCE_PATH_STYLE`.
`docker-compose.yml` contains `EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND`.
`docker-compose.yml` contains `EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET`.
`docs/local-stack.md` contains `S3-compatible` or `remote artifact storage`.
`docs/local-stack.md` contains a note that MinIO is not added to this stack.
`docs/artifact-delivery.md` contains `s3:`.
`docs/artifact-delivery.md` contains `logical` or `opaque locator`.
`docs/artifact-delivery.md` contains guidance not to interpret `storage_uri` as a bucket or object identifier.</acceptance_criteria>
  <verify>
    <automated>rg -n "EDGAR_BACKEND_ARTIFACT_STORAGE_BACKEND|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_BUCKET|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_ENDPOINT_URL|EDGAR_BACKEND_ARTIFACT_STORAGE_S3_FORCE_PATH_STYLE|s3:|opaque locator|bucket or object" .env.example docker-compose.yml docs/local-stack.md docs/artifact-delivery.md</automated>
  </verify>
  <done>The local stack and artifact-delivery docs now explain how to opt into remote storage without changing the local default or weakening the delivery contract.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_artifact_content_delivery.py tests/test_artifact_storage_s3.py -q --tb=short` after Task 1, then use the `rg` command in Task 2 so the remote delivery contract and ops docs stay aligned.
</verification>

<success_criteria>
Phase 07 is complete once S3-backed artifacts prove they still flow through the same application-owned metadata or content surfaces, and operators can enable the backend through documented env vars without turning storage topology into a product contract.
</success_criteria>

<output>
After completion, create `.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-03-SUMMARY.md`
</output>
