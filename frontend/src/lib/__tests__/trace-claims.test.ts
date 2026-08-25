import { describe, expect, it } from "vitest";

import type { InvestigationDetail } from "@/lib/api/types";
import { claimTrace, claimVerdict } from "@/lib/trace-claims";

/**
 * The trace regrouped around claims. What matters is that nothing is attributed by guess:
 * a step lands under a claim only when the run recorded that link, and everything else stays
 * visible in a bucket rather than being quietly filed somewhere plausible.
 */
function detail(over: Partial<InvestigationDetail> = {}): InvestigationDetail {
  return {
    id: "inv-1", domain_id: "inv-1", analysis_run_id: "run-1", project_id: null,
    origin: "native",
    dataset_origin: "synthetic", status: "converged", confidence: 0.95, objective: "why?",
    adapter_id: "edgar", conclusion: null, demo_slug: "d",
    counts: {
      hypotheses: 0, evidence: 0, experiments: 0, observations: 0,
      decisions: 0, critiques: 0, open_questions: 0,
    },
    outcome: {
      kind: "supported", termination_reason: "sufficient_evidence",
      claims_supported: 0, claims_rejected: 0, claims_weakened: 0, claims_unresolved: 0,
      contradiction_found: false,
    },
    created_at: "2026-08-20T19:02:18Z", updated_at: "2026-08-20T19:02:30Z",
    success_criteria: [], constraints: [], termination: null,
    hypotheses: [], evidence: [], experiments: [], observations: [],
    decisions: [], critiques: [], open_questions: [],
    conclusion_detail: null, datasets: [], events: [],
    ...over,
  };
}

const claim = (id: string, statement: string, status = "supported") =>
  ({ id, statement, status, confidence: 0.95 }) as never;

const decision = (id: string, sequence: number, targets: string[], type = "revise_confidence") =>
  ({
    id, sequence, decision_type: type, rationale: "because", iteration: 0,
    chosen_option: null, alternatives: [],
    targets: targets.map((t) => ({ kind: "hypothesis", id: t })),
  }) as never;

describe("claimTrace", () => {
  it("gives each claim its verdict and confidence from the run", () => {
    const trace = claimTrace(
      detail({ hypotheses: [claim("h-0", "staffing drives it", "weakened")] }),
    );

    expect(trace.claims[0]).toMatchObject({
      statement: "staffing drives it",
      status: "weakened",
      verdict: "Did not hold",
      confidence: 0.95,
    });
  });

  it("files a decision under the claim it named", () => {
    const trace = claimTrace(
      detail({
        hypotheses: [claim("h-0", "a"), claim("h-1", "b")],
        decisions: [decision("d-0", 0, ["h-1"])],
      }),
    );

    expect(trace.claims[0].steps).toHaveLength(0);
    expect(trace.claims[1].steps).toHaveLength(1);
    expect(trace.shared).toHaveLength(0);
  });

  it("puts a step under every claim it acted on, not just the first", () => {
    // A contradiction weakens two claims in one act; filing it under one would hide it
    // from the other, which is the claim a reader is checking.
    const trace = claimTrace(
      detail({
        hypotheses: [claim("h-0", "a"), claim("h-1", "b")],
        decisions: [decision("d-0", 0, ["h-0", "h-1"])],
      }),
    );

    expect(trace.claims[0].steps).toHaveLength(1);
    expect(trace.claims[1].steps).toHaveLength(1);
    // Distinct keys, or React collapses the two rows into one.
    expect(trace.claims[0].steps[0].id).not.toBe(trace.claims[1].steps[0].id);
  });

  it("keeps a step that names no claim rather than attributing it", () => {
    const trace = claimTrace(
      detail({ hypotheses: [claim("h-0", "a")], decisions: [decision("d-0", 0, [])] }),
    );

    expect(trace.claims[0].steps).toHaveLength(0);
    expect(trace.shared).toHaveLength(1);
  });

  it("ignores a decision aimed at an experiment rather than a claim", () => {
    const aimedAtExperiment = {
      id: "d-0", sequence: 0, decision_type: "select_experiment", rationale: "r",
      iteration: 0, chosen_option: "analyze_correlation", alternatives: [],
      targets: [{ kind: "experiment_request", id: "exp-0" }],
    } as never;

    const trace = claimTrace(
      detail({ hypotheses: [claim("h-0", "a")], decisions: [aimedAtExperiment] }),
    );

    expect(trace.claims[0].steps).toHaveLength(0);
    expect(trace.shared).toHaveLength(1);
  });

  it("attaches an experiment to the claims it was raised to test", () => {
    const trace = claimTrace(
      detail({
        hypotheses: [claim("h-0", "a")],
        experiments: [
          {
            id: "x-0", tool_name: "analyze_correlation", status: "succeeded",
            summary: "ran", metrics: null, error: null, request_domain_id: "exp-0",
            target_hypothesis_ids: ["h-0"], created_at: "2026-08-20T19:02:18Z", artifacts: [],
          } as never,
        ],
      }),
    );

    expect(trace.claims[0].experiments).toEqual(["analyze_correlation"]);
    expect(trace.claims[0].steps.some((s) => s.kind === "experiment")).toBe(true);
  });

  it("does not attribute an experiment whose request was never recorded", () => {
    // Every run before request persistence looks like this. It must read as unknown.
    const trace = claimTrace(
      detail({
        hypotheses: [claim("h-0", "a")],
        experiments: [
          {
            id: "x-0", tool_name: "analyze_correlation", status: "succeeded",
            summary: null, metrics: null, error: null, request_domain_id: null,
            target_hypothesis_ids: [], created_at: "2026-08-20T19:02:18Z", artifacts: [],
          } as never,
        ],
      }),
    );

    expect(trace.claims[0].experiments).toEqual([]);
    expect(trace.shared.some((s) => s.kind === "experiment")).toBe(true);
  });

  it("counts evidence for and against each claim separately", () => {
    const ev = (id: string, direction: string) =>
      ({ id, claim: "c", hypothesis_ids: ["h-0"], direction }) as never;

    const trace = claimTrace(
      detail({
        hypotheses: [claim("h-0", "a")],
        evidence: [ev("e-0", "supports"), ev("e-1", "supports"), ev("e-2", "refutes")],
      }),
    );

    expect(trace.claims[0].supportingEvidence).toBe(2);
    expect(trace.claims[0].refutingEvidence).toBe(1);
  });

  it("orders a claim's steps by when they happened", () => {
    const trace = claimTrace(
      detail({
        hypotheses: [claim("h-0", "a")],
        decisions: [decision("d-late", 5, ["h-0"]), decision("d-early", 1, ["h-0"])],
      }),
    );

    expect(trace.claims[0].steps.map((s) => s.id)).toEqual(["h-0:d-early", "h-0:d-late"]);
  });

  it("has nothing to show for a run that proposed no claims", () => {
    const trace = claimTrace(detail());

    expect(trace.claims).toEqual([]);
  });
});

describe("claimVerdict", () => {
  it("says in words what the status means", () => {
    expect(claimVerdict("supported")).toBe("Held up");
    expect(claimVerdict("weakened")).toBe("Did not hold");
    expect(claimVerdict("unresolved")).toBe("Left unresolved");
  });

  it("falls back to the raw status rather than inventing a reading", () => {
    expect(claimVerdict("something_new")).toBe("something_new");
  });
});
