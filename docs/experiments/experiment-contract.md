# Experiment Contract

A **deterministic experiment** is a typed analytical operation that accepts
declared dataset capabilities and typed parameters, performs deterministic
computation, returns structured observations and evidence, and emits reproducible
artifacts. **No experiment calls an LLM for numerical output.**

Code: `agentic/experiments/`. It builds on the domain model
(`agentic/domain/`) and the input adapters (`agentic/adapters/`). Nothing here is
wired into production orchestration yet.

## Core abstractions

| Abstraction | File | Responsibility |
|---|---|---|
| `ExperimentTool` (Protocol) + `BaseExperimentTool` | `base.py` | The tool interface; the base implements parsing, validation, fingerprinting, and structured failure so a tool only writes `descriptor()` + `_compute()`. |
| `ExperimentRegistry` | `registry.py` | Register/look up tools by name; `build_default_registry()` seeds the general + EDGAR tools. |
| `ExperimentCapability` | `capability.py` | What a tool *requires* of a dataset (modalities, roles, min rows, temporal/entity). |
| `ExperimentValidationResult` | `capability.py` | Outcome of validating params + capabilities (structured `ValidationIssue`s). |
| `ExperimentContext` | `context.py` | The transient run bundle: manifest, materialized frame/documents, raw params, artifact sink, provenance. |
| `ExperimentExecutionRecord` | `record.py` | The serializable audit of one run: outputs, fingerprints, status, timing, reproducibility. Maps to the domain `ExperimentResult`. |
| `ExperimentError` (+ subclasses) | `errors.py` | Structured failures with stable `code`; never raw framework exceptions. |
| `ExperimentToolDescriptor` | `descriptor.py` | The self-describing contract each tool declares. |
| `ArtifactSink` / `ArtifactRecord` | `artifacts.py` | Content-addressed emission of tables, JSON, and chart specs. |

## What every tool declares (`ExperimentToolDescriptor`)

`name`, `version`, `purpose`, `supported_input_modalities`,
`required_capabilities`, `parameter_schema` (JSON schema of the typed params),
`output_schema` (declared output fields), `cost_estimate`, `deterministic` flag,
`artifact_types`, and `known_limitations`.

## Lifecycle of a run

```
tool.run(ExperimentContext)
  1. validate(params, manifest)            -> ExperimentValidationResult
       - parse params via the typed model (rejects bad types / missing fields)
       - check_capability(required, manifest) (modality, roles, temporal, rows)
       - _check_params_against_manifest (columns referenced actually exist)
     invalid -> failed ExperimentExecutionRecord (status=failed, structured error)
  2. _compute(context, params)             -> ExperimentOutcome   (deterministic)
       - observations, evidence (+ statistics), metrics, artifacts, warnings
     raises ExperimentError / any Exception -> failed record (normalized)
  3. assemble ExperimentExecutionRecord
       - dataset_fingerprint (from manifest)
       - input_fingerprint  = hash(dataset + tool + version + canonical params)
       - output_fingerprint = hash(content of observations/evidence/metrics/artifacts,
                                    excluding volatile ids/timestamps)
```

## Determinism & reproducibility

- Computation uses numpy/pandas only (no LLM, no randomness). Given the same
  dataset and params, a tool produces the **same `output_fingerprint`** every run
  — even though entity ids and timestamps differ (they are excluded from the
  output hash). Proven by `test_deterministic_repeatability`.
- Artifacts are content-addressed (`sha256`); identical computations emit
  byte-identical, identically-fingerprinted artifacts.
- Every record carries a `ReproducibilityManifest` (tool versions) and the
  `input_fingerprint` that identifies the exact computation.

## Structured outputs

- **Observations** (`agentic.domain.Observation`) — raw noticed facts (a value, an
  outlier, a trend), each with a verifiable data reference.
- **Evidence** (`agentic.domain.Evidence`) — interpreted findings with an explicit
  `direction` and bounded `strength`/`reliability`/`coverage` derived
  deterministically from the statistics (see below).
- **Metrics** — named scalars for quick comparison/termination checks.
- **Artifacts** — tables (CSV), JSON summaries, and chart specs.

## Statistical outputs

Where statistically applicable, a tool attaches a `StatisticalSummary`
(`agentic.domain.statistics`) carrying: **effect size** (+ its kind),
**uncertainty** (confidence interval / standard error), **sample size**,
**assumptions**, **diagnostics**, **warnings**, and **coverage**. These are the
*evidence strength inputs*: `stats.evidence_strength(summary)` maps them
deterministically to bounded `(strength, reliability, coverage)` on the evidence
record — strength from the normalized effect size (p-value fallback), reliability
from sample size (penalized when assumptions/warnings apply), coverage from the
summary. p-values use a documented normal / large-sample approximation so the
system stays dependency-free (no scipy); effect sizes are the primary signal.

## Failure model

| Error | code | When |
|---|---|---|
| `ExperimentValidationError` | `EXPERIMENT_VALIDATION` | params or capabilities invalid |
| `CapabilityError` | `CAPABILITY_UNSATISFIED` | dataset lacks required capability |
| `ParameterError` | `INVALID_PARAMETER` | missing/ill-typed param or absent column at runtime |
| `ExperimentExecutionError` | `EXPERIMENT_EXECUTION` | deterministic computation failed |
| `UnknownExperimentError` | `UNKNOWN_EXPERIMENT` | tool not registered |

`run()` never raises for validation/compute failure — it returns a
`ExperimentExecutionRecord` with `status=failed` and a structured `error`, so
callers always get an auditable record.

## Writing a new tool

1. Subclass `BaseExperimentTool`; set `params_model` (a `DomainModel` subclass).
2. Implement `descriptor()` with the full contract above.
3. Implement `_compute(context, params) -> ExperimentOutcome` deterministically.
4. Override `_check_params_against_manifest` to verify column params exist.
5. Register in `build_default_registry()` (or a custom registry).

Domain specificity (e.g. EDGAR column meanings) belongs in the tool or its
manifest hints — never in the general statistics/validation layer.
