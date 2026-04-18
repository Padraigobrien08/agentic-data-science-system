---
phase: 07-remote-artifact-storage-contract
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - requirements-backend.txt
  - requirements-dev.txt
  - backend/config/settings.py
  - backend/storage/factory.py
  - backend/storage/resolver.py
  - backend/storage/s3.py
  - tests/test_artifact_storage_s3.py
autonomous: true
requirements:
  - STOR-01
must_haves:
  truths:
    - "One deployment setting can switch new artifact writes from local disk to an S3-compatible backend without changing artifact IDs or product routes."
    - "Persisted `s3:` locators stay app-owned logical URIs and do not embed the configured bucket name."
    - "Legacy `local:` artifacts remain readable even when the configured write backend is S3."
  artifacts:
    - path: backend/storage/s3.py
      provides: "First S3-compatible object-store backend behind the existing protocol"
    - path: backend/config/settings.py
      provides: "Explicit remote-storage configuration surface with local-safe defaults"
    - path: backend/storage/factory.py
      provides: "Configured write-backend selection"
    - path: backend/storage/resolver.py
      provides: "Scheme-dispatched mixed-read support for `local:` and `s3:` URIs"
    - path: tests/test_artifact_storage_s3.py
      provides: "Moto-backed contract coverage for S3 store behavior and resolver dispatch"
  key_links:
    - from: backend/config/settings.py
      to: backend/storage/factory.py
      via: "settings select the deployment write backend"
      pattern: "artifact_storage_backend|get_object_store"
    - from: backend/storage/s3.py
      to: backend/storage/resolver.py
      via: "resolver opens and deletes `s3:` locators through the new store"
      pattern: "s3:|open_reader|delete_at_uri"
---

<objective>
Add the remote backend foundation: settings, S3-compatible object store, and scheme-dispatched resolver support.

Purpose: satisfy the backend-selection part of `STOR-01` before artifact-service, retention, or route behavior depends on the new backend.
Output: one S3-compatible object store, a configurable write-backend selector, mixed-read resolver support, and backend contract tests.
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
@backend/config/settings.py
@backend/storage/protocol.py
@backend/storage/local.py
@backend/storage/factory.py
@backend/storage/resolver.py
@backend/storage/types.py
@tests/test_artifact_storage.py
@docs/artifact-delivery.md

<interfaces>
From `backend/storage/protocol.py`:
```python
class ArtifactObjectStore(Protocol):
    @property
    def scheme(self) -> str: ...
    def make_uri(self, key: str) -> str: ...
    def key_from_uri(self, uri: str) -> str: ...
    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> StoredObject: ...
    def put_fileobj(self, key: str, source: BinaryIO, *, content_type: str | None = None) -> StoredObject: ...
    def open_reader(self, key: str) -> Iterator[BinaryIO]: ...
    def exists(self, key: str) -> bool: ...
    def delete(self, key: str) -> None: ...
    def list_keys_under(self, prefix: str) -> list[str]: ...
```

From `backend/storage/resolver.py`:
```python
def read_bytes(uri: str, *, settings: Settings | None = None) -> bytes: ...
def open_reader(uri: str, *, settings: Settings | None = None) -> Iterator[BinaryIO]: ...
def delete_at_uri(uri: str, *, settings: Settings | None = None) -> None: ...
```

From `backend/config/settings.py`:
```python
class Settings(BaseSettings):
    artifact_storage_root: Path
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Add S3-compatible backend settings and object-store implementation</name>
  <files>requirements-backend.txt
requirements-dev.txt
backend/config/settings.py
backend/storage/s3.py
tests/test_artifact_storage_s3.py</files>
  <read_first>.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
backend/config/settings.py
backend/storage/protocol.py
backend/storage/local.py
backend/storage/types.py
tests/test_artifact_storage.py</read_first>
  <behavior>
    - Per D-01 and D-02, the repo gains exactly one S3-compatible backend using AWS S3 semantics with optional endpoint override support.
    - Per D-05, persisted remote URIs use the logical `s3:` scheme and do not embed the configured bucket name.
    - Per D-08, upload digest truth remains the app-computed SHA-256, not provider ETag behavior.
  </behavior>
  <action>Add `boto3>=1.42.91` to `requirements-backend.txt` and `moto[s3]>=5.1.22` to `requirements-dev.txt`. Extend `backend/config/settings.py` with the exact additive fields `artifact_storage_backend: str = "local"`, `artifact_storage_s3_bucket: str | None = None`, `artifact_storage_s3_region: str = "us-east-1"`, `artifact_storage_s3_prefix: str = ""`, `artifact_storage_s3_endpoint_url: str | None = None`, `artifact_storage_s3_access_key_id: str | None = None`, `artifact_storage_s3_secret_access_key: SecretStr | None = None`, and `artifact_storage_s3_force_path_style: bool = False`, plus validation that `artifact_storage_s3_bucket` is required when the backend is `s3`. Create `backend/storage/s3.py` with `class S3ObjectStore` implementing the existing protocol through `boto3.client("s3", ...)`. `make_uri()` must return `s3:{logical_key}` with the same percent-encoding discipline as `local:`; the configured bucket and optional prefix stay internal. Implement `put_fileobj()` so it streams from the source, computes `sha256_hex` locally, uploads the object, and returns a `StoredObject` whose `uri` is the logical `s3:` locator. `get()`, `open_reader()`, `exists()`, `delete()`, and `list_keys_under()` must map missing objects to `ObjectNotFound`. Create `tests/test_artifact_storage_s3.py` with moto-backed contract tests for put/get/open/list/delete, `sha256_hex`, and an assertion that `stored.uri` starts with `s3:` but does not contain the configured bucket string.</action>
  <acceptance_criteria>`requirements-backend.txt` contains `boto3`.
`requirements-dev.txt` contains `moto[s3]`.
`backend/config/settings.py` contains `artifact_storage_backend`.
`backend/config/settings.py` contains `artifact_storage_s3_bucket`.
`backend/config/settings.py` contains `artifact_storage_s3_endpoint_url`.
`backend/config/settings.py` contains `artifact_storage_s3_force_path_style`.
`backend/storage/s3.py` exists.
`backend/storage/s3.py` contains `class S3ObjectStore`.
`backend/storage/s3.py` contains `return "s3"`.
`backend/storage/s3.py` contains `hashlib.sha256()`.
`tests/test_artifact_storage_s3.py` contains `moto`.
`tests/test_artifact_storage_s3.py` contains an assertion that the stored URI starts with `s3:`.
`tests/test_artifact_storage_s3.py` contains an assertion that the bucket name is absent from the stored URI.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_storage_s3.py -q --tb=short</automated>
  </verify>
  <done>The codebase now has one S3-compatible object store with a logical `s3:` locator contract and deterministic checksum behavior.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Add configured-write selection and mixed-read resolver dispatch</name>
  <files>backend/storage/factory.py
backend/storage/resolver.py
tests/test_artifact_storage_s3.py</files>
  <read_first>.planning/phases/07-remote-artifact-storage-contract/07-CONTEXT.md
.planning/phases/07-remote-artifact-storage-contract/07-RESEARCH.md
.planning/phases/07-remote-artifact-storage-contract/07-VALIDATION.md
backend/storage/factory.py
backend/storage/resolver.py
backend/storage/local.py
backend/storage/s3.py
tests/test_artifact_storage.py
tests/test_artifact_storage_s3.py</read_first>
  <behavior>
    - Per D-03 and D-04, deployments choose a default write backend through settings, but persisted URI scheme remains the source of truth for reads and deletes.
    - A deployment configured for S3 still reads legacy `local:` rows correctly, and a local deployment still treats unknown `s3:` rows as unsupported unless that backend is configured.
    - Resolver behavior stays generic and scheme-based rather than adding a second user-facing route or API surface.
  </behavior>
  <action>Refactor `backend/storage/factory.py` to expose `get_object_store(settings)` as the configured write backend plus helper(s) that resolve a store by URI scheme. Keep `LocalFilesystemStore` support intact, and add S3 backend selection when `artifact_storage_backend == "s3"`. Update `backend/storage/resolver.py` so `read_bytes()`, `open_reader()`, and `delete_at_uri()` dispatch by the URI scheme instead of hard-coding only `local:`. `local:` must continue to work regardless of the configured write backend, and `s3:` must resolve through the new store only when S3 is configured. Extend `tests/test_artifact_storage_s3.py` with mixed-read coverage that seeds one local object and one S3 object, asserts both schemes round-trip through the resolver, and asserts unsupported schemes still raise `UnsupportedStorageUri` without changing existing local-store behavior.</action>
  <acceptance_criteria>`backend/storage/factory.py` contains `get_object_store(`.
`backend/storage/factory.py` contains `artifact_storage_backend`.
`backend/storage/factory.py` contains `S3ObjectStore`.
`backend/storage/resolver.py` no longer hard-codes only `if uri.startswith("local:")`.
`backend/storage/resolver.py` contains `s3:`.
`backend/storage/resolver.py` contains `UnsupportedStorageUri`.
`tests/test_artifact_storage_s3.py` contains `read_bytes(` or `open_reader(` coverage for both `local:` and `s3:`.
`tests/test_artifact_storage_s3.py` contains `UnsupportedStorageUri`.
`python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short</automated>
  </verify>
  <done>The repo can now write to one configured backend while still reading legacy artifacts by their persisted scheme.</done>
</task>

</tasks>

<verification>
Run `python3 -m pytest tests/test_artifact_storage_s3.py -q --tb=short` after Task 1, then `python3 -m pytest tests/test_artifact_storage.py tests/test_artifact_storage_s3.py -q --tb=short` after Task 2 so the new backend and mixed-read resolver stay aligned with the existing local storage contract.
</verification>

<success_criteria>
Phase 07 has a valid storage foundation once one S3-compatible backend exists, the configured write backend is selectable through settings, and both `local:` and `s3:` locators resolve correctly through the same storage seam.
</success_criteria>

<output>
After completion, create `.planning/phases/07-remote-artifact-storage-contract/07-remote-artifact-storage-contract-01-SUMMARY.md`
</output>
