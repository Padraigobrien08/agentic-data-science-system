---
phase: 05-storage-and-ops
plan: 02
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/storage/protocol.py
  - backend/storage/local.py
  - backend/services/artifact_service.py
  - tests/test_artifact_storage.py
autonomous: true
requirements:
  - OPER-02
must_haves:
  truths:
    - "Artifact ingestion can move large pipeline outputs into managed storage without reading the whole file into memory first."
    - "The existing `local:` object-store contract, object-key layout, and artifact provenance metadata stay intact after the ingest refactor."
    - "Failed writes do not leave partially written final artifact blobs behind in the storage root."
  artifacts:
    - path: backend/storage/protocol.py
      provides: "Storage seam for streamed writes"
    - path: backend/storage/local.py
      provides: "Chunked temp-file copy plus SHA-256 hashing for the local object store"
    - path: backend/services/artifact_service.py
      provides: "Streamed pipeline-file ingest that preserves the existing artifact metadata contract"
    - path: tests/test_artifact_storage.py
      provides: "Regression coverage for streamed ingest, digest correctness, and no `Path.read_bytes()` dependence"
  key_links:
    - from: backend/services/artifact_service.py
      to: backend/storage/protocol.py
      via: "pipeline ingest delegates to the streamed storage write seam"
      pattern: "put_fileobj|ingest_pipeline_file"
    - from: backend/storage/local.py
      to: backend/services/artifact_service.py
      via: "LocalFilesystemStore returns the same StoredObject metadata used to persist Artifact rows"
      pattern: "StoredObject|sha256_hex|byte_size"
---

<objective>
Replace full-memory pipeline artifact ingest with streamed writes inside the existing storage abstraction.

Purpose: satisfy `OPER-02` without changing the current `local:` storage contract or widening the Phase 05 scope into remote object storage.
Output: a streamed object-store write method, a temp-file-safe local implementation, and artifact-service regressions that prove pipeline ingest no longer depends on `Path.read_bytes()`.
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
@.planning/phases/05-storage-and-ops/05-CONTEXT.md
@.planning/phases/05-storage-and-ops/05-RESEARCH.md
@.planning/phases/05-storage-and-ops/05-VALIDATION.md
@.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
@.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md
@backend/storage/protocol.py
@backend/storage/local.py
@backend/services/artifact_service.py
@tests/test_artifact_storage.py
@tests/test_run_isolation_execution_service.py

<interfaces>
From `backend/storage/protocol.py`:
```python
class ArtifactObjectStore(Protocol):
    def put(self, key: str, data: bytes, *, content_type: str | None = None) -> StoredObject: ...
    @contextmanager
    def open_reader(self, key: str) -> Iterator[BinaryIO]: ...
```

From `backend/storage/types.py`:
```python
@dataclass(frozen=True, slots=True)
class StoredObject:
    uri: str
    byte_size: int
    sha256_hex: str | None = None
    content_type: str | None = None
```

From `backend/services/artifact_service.py`:
```python
def ingest_pipeline_file(
    self,
    source_path: Path | str,
    *,
    role_key: str,
    analysis_run_id: UUID | None = None,
    evaluation_run_id: UUID | None = None,
    run_step_id: UUID | None = None,
    meta_json: dict | list | None = None,
) -> Artifact: ...
```
</interfaces>
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Extend the storage abstraction with streamed local-file writes</name>
  <files>backend/storage/protocol.py
backend/storage/local.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
backend/storage/protocol.py
backend/storage/local.py
backend/storage/types.py</read_first>
  <behavior>
    - Per D-03, the storage seam supports writing from an open binary stream in bounded chunks instead of requiring a pre-built `bytes` object.
    - Per D-04, the `local:` URI contract and safe relative-key enforcement stay unchanged.
    - Failed streamed writes do not publish partial final files because the local store stages through a same-directory temp file and only swaps into place on success.
  </behavior>
  <action>Add `put_fileobj(self, key: str, source: BinaryIO, *, content_type: str | None = None) -> StoredObject` to `backend/storage/protocol.py`. Implement the same method in `backend/storage/local.py` using Python stdlib only: open a temp file created with `tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")`, stream `1024 * 1024` byte chunks from `source.read(...)`, update `hashlib.sha256()`, count total bytes, and finish with `os.replace(tmp_name, path)`. On any exception, remove the temp file with `Path(tmp_name).unlink(missing_ok=True)` before re-raising. Keep `put(...)` working for existing callers by delegating through `io.BytesIO(data)` into `put_fileobj(...)` so all write paths share one hashing and temp-file implementation.</action>
  <acceptance_criteria>`backend/storage/protocol.py` contains `def put_fileobj(`.
`backend/storage/local.py` contains `def put_fileobj(`.
`backend/storage/local.py` contains `tempfile.mkstemp`.
`backend/storage/local.py` contains `os.replace(`.
`backend/storage/local.py` contains `hashlib.sha256()`.
`backend/storage/local.py` contains `io.BytesIO(` or an equivalent delegation from `put(` into `put_fileobj(`.
`backend/storage/local.py` still contains `def put(` so current callers remain supported.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_storage.py -q --tb=short</automated>
  </verify>
  <done>The storage abstraction can now stream writes safely through the local backend without changing the persisted URI or key contract.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Route pipeline artifact ingest through the streamed storage seam</name>
  <files>backend/services/artifact_service.py
tests/test_artifact_storage.py</files>
  <read_first>.planning/phases/05-storage-and-ops/05-CONTEXT.md
.planning/phases/05-storage-and-ops/05-RESEARCH.md
.planning/phases/05-storage-and-ops/05-VALIDATION.md
.planning/phases/01-run-isolation/01-run-isolation-03-SUMMARY.md
.planning/phases/03-secure-defaults/03-secure-defaults-02-SUMMARY.md
backend/services/artifact_service.py
backend/storage/protocol.py
backend/storage/local.py
tests/test_artifact_storage.py
tests/test_run_isolation_execution_service.py</read_first>
  <behavior>
    - Per D-03, `ArtifactService.ingest_pipeline_file(...)` opens the source file and streams it into managed storage instead of calling `Path.read_bytes()`.
    - Per D-04, the ingested `Artifact` row keeps the same role-key-based object path, `source_filename`, `source_workspace_relative_path`, `byte_size`, and `content_sha256` contract established by earlier phases.
    - Existing `save_bytes(...)`, `ingest_json_payload(...)`, and `ingest_text_document(...)` behavior remains additive and compatible.
  </behavior>
  <action>Refactor `backend/services/artifact_service.py` so the object-key generation and `Artifact` row insertion live in a shared private helper, then add a streamed branch used only by `ingest_pipeline_file(...)`. Replace `data = path.read_bytes()` with `with path.open("rb") as fh:` plus `self._store.put_fileobj(key, fh, content_type=mime)` while preserving the same `ArtifactKind`, MIME detection, provenance metadata merge, and `storage_uri` layout. Do not change the `safe_role_segment(...)` key structure or the run-workspace-relative provenance keys introduced earlier. Extend `tests/test_artifact_storage.py` with one regression that monkeypatches `Path.read_bytes` to raise during `ingest_pipeline_file(...)` and still succeeds, and one regression that forces a local-store write failure and asserts the destination directory has no leftover `.<name>.*.tmp` file after the exception.</action>
  <acceptance_criteria>`backend/services/artifact_service.py` no longer contains `data = path.read_bytes()` inside `ingest_pipeline_file`.
`backend/services/artifact_service.py` contains `with path.open("rb")`.
`backend/services/artifact_service.py` contains `put_fileobj(`.
`backend/services/artifact_service.py` still contains `source_workspace_relative_path`.
`tests/test_artifact_storage.py` contains the string `read_bytes should not be called`.
`tests/test_artifact_storage.py` contains an assertion about leftover temp files or `.tmp`.
`python3 -m pytest tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q --tb=short` passes.</acceptance_criteria>
  <verify>
    <automated>python3 -m pytest tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q --tb=short</automated>
  </verify>
  <done>Pipeline artifacts now move into managed storage through streamed writes while preserving the existing audit and provenance contract.</done>
</task>

</tasks>

<verification>
Use `python3 -m pytest tests/test_artifact_storage.py tests/test_run_isolation_execution_service.py -q --tb=short` after each task so the streamed ingest refactor stays compatible with the existing artifact metadata and workspace-provenance contract.
</verification>

<success_criteria>
Phase 05 can trust large-file artifact ingest once `ArtifactService` no longer depends on full-memory reads and the local object-store seam performs chunked, hash-preserving, temp-file-safe writes.
</success_criteria>

<output>
After completion, create `.planning/phases/05-storage-and-ops/05-storage-and-ops-02-SUMMARY.md`
</output>
