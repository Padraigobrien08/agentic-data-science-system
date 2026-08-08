# Termination Policy, Budgets, and Safety Limits

The loop never runs unbounded. `TerminationPolicy` (`agentic/agent/components.py`)
decides continue/stop each iteration and returns a typed `TerminationReason`
before any conclusion is synthesized. Budgets and safety limits
(`agentic/agent/budget.py`) bound the run.

## Termination reasons

Every terminal state is one explicit `TerminationReason`
(`agentic/domain/enums.py`):

| Reason | When |
|---|---|
| `sufficient_evidence` | **every** hypothesis has been investigated (none still `proposed`), at least one is supported at ≥ `SUFFICIENT_CONFIDENCE` (0.6), and **each** supported one has been challenged (a suggested falsification tool has run) or has no unused falsification tool left. |
| `insufficient_evidence` | candidates are exhausted (experiments ran) with no supported hypothesis. |
| `budget_exhausted` | any budget dimension reached (experiments / model calls / elapsed time / cost). |
| `no_valid_experiment` | no valid candidate ever existed (e.g. dataset fails every tool's capability). |
| `repeated_failure` | consecutive experiment failures reached the safety cap. |
| `user_stop` | a stop was requested. |
| `safety_constraint` | a hard safety limit was hit (max iterations, absolute elapsed cap). |
| `error` | an internal error / malformed model response — the loop fails safely. |

Order of checks each iteration (first match wins): user stop → safety → repeated
failure → budget → sufficient evidence. When the selector finds no candidate, the
loop finalizes with `sufficient_evidence` / `insufficient_evidence` /
`no_valid_experiment` depending on whether any experiment ran and any hypothesis
is supported.

**Sufficiency requires challenge.** The loop does not declare success on the first
supporting result: a supported claim must survive (or exhaust) a critic-proposed
falsification experiment before `sufficient_evidence` is returned. This is what
makes the agent adversarial rather than a one-shot pipeline. The requirement applies
**per supported claim** — one claim surviving a falsification says nothing about the others.

**Sufficiency is about the investigation, not one claim.** An investigation holding several
hypotheses is not done because the first one landed. Stopping there strands the rest at
`proposed`, never investigated, while the run reports success.

The bar is "no hypothesis is still `proposed`", deliberately *not* `Hypothesis.is_terminal()`:
only `rejected` is terminal in the transition graph — a supported claim may still be weakened —
so requiring terminality would mean requiring every claim to be rejected. A claim past
`proposed` has had evidence brought to bear on it.

**A split outcome is `mixed`.** When some claims are supported and others rejected or weakened,
the conclusion's disposition is `mixed` rather than `supported`, its statement names both sides,
and its confidence averages across all of them. Reporting such a run as supported would drop a
refutation the user explicitly asked about. `mixed` is distinct from `inconclusive`: there the
evidence on a claim was equivocal, here it was clear and pointed different ways for different
claims.

## Budgets (soft, resource-based)

`LoopBudget` — the five required budgets, enforced by `BudgetTracker`:

| Budget | Field | Default |
|---|---|---|
| Maximum experiments | `max_experiments` | 8 — scales with claim count, see below |
| Maximum model calls | `max_model_calls` | 40 |
| Maximum elapsed time | `max_elapsed_seconds` | 120 |
| Maximum estimated cost | `max_cost_usd` | 1.0 |
| Maximum repeated-tool usage | `max_repeated_tool_uses` | 3 |

`BudgetTracker` counts experiments, model calls (one per policy method call),
cost, elapsed time, and per-tool usage. `tool_at_limit(tool)` removes a tool from
candidates once its repeated-use cap is reached. Hitting any budget →
`budget_exhausted` (`test_budget_limits_bound_the_run`).

**Experiments scale with claim count**, not just goal difficulty: each hypothesis draws its own
candidates, parameterised to its own metric. Measured against the deterministic policy:

| Claims | Experiments | Outcome |
|---|---|---|
| 1 | 2 | `sufficient_evidence` |
| 2 | 3 | `sufficient_evidence` |
| 3 | 7 | `sufficient_evidence` |
| 4 | 8 | `budget_exhausted` |

The default of 8 lets a realistic multi-part question — two or three clauses — complete, while a
runaway one stops with a typed reason rather than silently truncating. Raise it if you routinely
ask four-part questions; worst-case cost and latency rise proportionally.

## Safety limits (hard, deterministic)

`SafetyLimits` are independent of budgets and always apply:

| Limit | Field | Default |
|---|---|---|
| Max iterations | `max_iterations` | 25 |
| Max consecutive failures | `max_consecutive_failures` | 3 |
| Absolute max elapsed | `absolute_max_elapsed_seconds` | 600 |

`max_iterations` and the absolute elapsed cap guarantee the loop always halts even
if budgets are misconfigured (→ `safety_constraint`); consecutive failures →
`repeated_failure`. These are the deterministic backstops that make the loop safe
to run unattended.

## Conclusion synthesis (only after termination)

`ConclusionSynthesizer` runs **once, after** a `TerminationReason` is decided, and
maps state to a `ConclusionDisposition`:

| State | Disposition |
|---|---|
| any supported hypothesis | `supported` (confidence = mean of supported) |
| only rejected | `refuted` |
| weakened / mixed | `inconclusive` |
| none of the above | `insufficient_evidence` |

Before synthesizing, any still-`active` hypothesis is set to `unresolved` — so
"remain unresolved" is an explicit, persisted outcome, not an omission. The
conclusion records supporting hypothesis ids, key evidence ids, caveats (including
the termination reason, preserved contradicting evidence, and open questions), and
the open-question ids. A `TerminationDecision` is written to state, and the
investigation status is set to `converged` (sufficient), `failed` (error / safety),
or `exhausted` (everything else).

## Budgets vs. safety — why both

Budgets express *intent* ("spend at most this much effort") and are tunable per
run; safety limits express *invariants* ("never loop forever, never thrash on
failures") and are not meant to be relied on as normal stopping conditions. A
healthy run stops on `sufficient_evidence` or `insufficient_evidence`; budgets
cap cost; safety limits catch bugs and pathological inputs.
