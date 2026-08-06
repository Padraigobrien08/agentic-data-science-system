# Extending the Platform

Three seams are designed to be extended without touching the loop:

| You want to… | Seam | Reference |
|---|---|---|
| Analyze a **new kind of data source** | Input adapter | [adapter contract](adapters/adapter-contract.md) |
| Give the agent a **new deterministic capability** | Experiment tool | [experiment contract](experiments/experiment-contract.md) |
| Change **how the agent decides** | `AgentPolicy` | [decision policy](agent/decision-policy.md) |

The contracts document the full surface. This page is the worked path through it.

> The example below is executed by `tests/agentic/test_extension_example.py`. If extending
> the platform stops working the way this describes, the build fails — the guide cannot
> silently rot.

## Adding an experiment tool

Experiment tools are where all computation lives. **They are deterministic**: same frame in,
same numbers out, no model call, no network. The policy chooses *which* tool runs; the tool
decides nothing.

### 1. Declare typed parameters

```python
class CoefficientOfVariationParams(DomainModel):
    column: str = Field(..., min_length=1, description="Numeric column to measure.")
```

Parameters are a model, not a dict, so a bad call becomes a structured validation issue
rather than an exception inside your computation.

### 2. Describe the tool

```python
class CoefficientOfVariationTool(BaseExperimentTool):
    params_model = CoefficientOfVariationParams

    def descriptor(self) -> ExperimentToolDescriptor:
        return ExperimentToolDescriptor(
            name="coefficient_of_variation",
            version="1.0",
            purpose="Relative variability of a numeric column (std / mean).",
            supported_input_modalities=["tabular", "time_series"],
            required_capabilities=ExperimentCapability(
                supported_modalities=["tabular", "time_series"],
                required_roles=[ColumnRole.metric],
                min_rows=2,
            ),
            parameter_schema=CoefficientOfVariationParams.model_json_schema(),
            output_schema=[OutputField(name="cv", kind="statistic")],
            artifact_types=[ArtifactType.json],
            known_limitations=["Undefined when the mean is zero."],
        )
```

`required_capabilities` is what makes the planner able to *rule your tool out* before running
it. Declaring `required_roles=[ColumnRole.metric]` means the tool is never proposed for a
dataset with no metric column. Be honest in `known_limitations`: it is surfaced to the agent.

### 3. Compute

```python
    def _check_params_against_manifest(self, params, manifest):
        return ensure_columns([params.column], manifest)

    def _compute(self, context, params) -> ExperimentOutcome:
        frame = require_frame(context)
        finite = numeric_array(frame, params.column)
        finite = finite[np.isfinite(finite)]
        mean = float(np.mean(finite))
        if abs(mean) < 1e-12:
            raise ParameterError("coefficient of variation is undefined for a zero mean")
        cv = float(np.std(finite, ddof=1)) / abs(mean)

        artifact = context.artifact_sink.emit_json(
            "coefficient_of_variation", {"column": params.column, "cv": round(cv, 6)}
        )
        return ExperimentOutcome(
            summary=f"Coefficient of variation for '{params.column}' is {cv:.3f}.",
            metrics={"cv": round(cv, 6)},
            statistics=[make_statistics(sample_size=int(finite.size), coverage=1.0,
                                        diagnostics={"cv": round(cv, 6)})],
            artifacts=[artifact],
        )
```

Raising `ParameterError` inside `_compute` is the supported way to fail: the base class turns
it into a record with `status=failed` and a populated `error`. **A tool never raises across the
loop boundary** — a failed experiment is ordinary loop vocabulary that counts toward the
consecutive-failure safety cap.

Emit artifacts through `context.artifact_sink`, never by writing files directly. The sink
content-addresses the bytes so identical computations produce identical fingerprints, and the
backend ingests whatever it collected.

### 4. Register and run

```python
registry = build_default_registry()
registry.register(CoefficientOfVariationTool())

investigation = InvestigationLoop(registry=registry).start(goal, manifest=manifest, frame=frame)
```

Registering a name that already exists raises — names are the tool's identity, so a collision
is an error rather than a silent shadow.

To make the loop *reach for* your tool by intent, add it to `INTENT_TOOLS` in
`agentic/agent/components.py`. Without that, it is available but only chosen as a fallback
candidate.

## Adding an input adapter

Same shape, different seam: an adapter turns some source into a `DatasetManifest` (+ optionally
a frame). The rules that matter:

- **`build_manifest` must not require the network.** Deterministic fixture execution depends on
  it, which is why the EDGAR adapter can describe its panel offline.
- **Declare structure, never domain vocabulary.** An adapter says "this column is the time
  index, that one is a metric"; it does not teach the loop what a *ticker* is. Domain knowledge
  enters as hints (`role_hints`, `semantic_hints`, `unit_hints`), not as loop behavior.
- **Failures are structured**, not exceptions.

`agentic/adapters/tabular.py` is the smallest complete example to copy.

## The rule the whole design rests on

**Nothing in the loop may depend on column names.** The loop reasons over *roles* declared by
an adapter. This is not aspirational — `suite_agency_v1` includes cases over weather-station
rainfall and service-latency data whose column names share nothing with the financial
fixtures, and a test asserts that non-overlap.

That check earns its keep: it caught a real bug where direction keywords were matched as
substrings, so `rainfall_mm is increasing` matched *fall* and the loop rejected a hypothesis
its own data supported. See `agentic/agent/direction.py`.

## Verifying your extension

```bash
python -m agentic.evaluation        # agency suite — did you change how the agent reasons?
pytest tests/agentic -q             # loop, adapters, experiments
```

If your change is meant to improve the agent's reasoning, [replay](agent/replay-and-diff.md)
persisted investigations against the new behavior and diff the conclusions — that answers
"did this actually change the analysis, or only the route to it?"
