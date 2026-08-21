import { describe, expect, it } from "vitest";

import type { InvestigationDetail } from "@/lib/api/types";
import { composeAnswer } from "@/lib/demo-answer";

/**
 * The assistant turn of a recorded run is assembled from persisted state, never written.
 * These tests are mostly about what it must *not* do: state a figure the run does not carry,
 * or imply a conversation that was never recorded.
 */
function detail(over: Partial<InvestigationDetail> = {}): InvestigationDetail {
  return {
    id: "inv-1",
    domain_id: "inv-1",
    analysis_run_id: "run-1",
    project_id: null,
    origin: "native",
    status: "exhausted",
    confidence: 0.4,
    objective: "does staffing or volume drive service?",
    adapter_id: "in_memory",
    conclusion: null,
    demo_slug: "a-demo",
    counts: {
      hypotheses: 2,
      evidence: 13,
      experiments: 3,
      observations: 0,
      decisions: 15,
      critiques: 2,
      open_questions: 2,
    },
    outcome: {
      kind: "contradicted",
      termination_reason: "insufficient_evidence",
      claims_supported: 0,
      claims_rejected: 0,
      claims_weakened: 2,
      claims_unresolved: 0,
      contradiction_found: true,
    },
    created_at: "2026-08-20T19:02:18Z",
    updated_at: "2026-08-20T19:02:30Z",
    success_criteria: [],
    constraints: [],
    termination: { reason: "insufficient_evidence", rationale: null, at_iteration: 3 } as never,
    hypotheses: [],
    evidence: [],
    experiments: [],
    observations: [],
    decisions: [],
    critiques: [],
    open_questions: [],
    conclusion_detail: null,
    datasets: [],
    events: [],
    ...over,
  };
}

describe("composeAnswer", () => {
  it("leads with what the run established, from the outcome classification", () => {
    const answer = composeAnswer(detail());

    expect(answer.headline).toBe(
      "Two claims could not both be true, so neither was allowed to stand.",
    );
  });

  it("reports the run's own counts and where it stopped", () => {
    const answer = composeAnswer(
      detail({ datasets: [{ name: "operational_delivery", row_count: 96 } as never] }),
    );

    expect(answer.footnote).toBe(
      "15 decisions, 3 experiments, 13 evidence items over operational_delivery (n=96), " +
        "stopping at insufficient_evidence.",
    );
  });

  it("says nothing about a dataset or a stopping point it does not have", () => {
    // A run with no dataset recorded must not gain one in the retelling.
    const answer = composeAnswer(detail({ datasets: [], termination: null }));

    expect(answer.footnote).toBe("15 decisions, 3 experiments, 13 evidence items.");
    expect(answer.footnote).not.toContain("over");
    expect(answer.footnote).not.toContain("stopping");
  });

  it("omits the row count when the dataset does not carry one", () => {
    const answer = composeAnswer({
      ...detail({ datasets: [{ name: "panel", row_count: null } as never] }),
    });

    expect(answer.footnote).toContain("over panel,");
    expect(answer.footnote).not.toContain("(n=");
  });

  it("singularises counts of one", () => {
    const answer = composeAnswer(
      detail({
        counts: { ...detail().counts, decisions: 1, experiments: 1, evidence: 1 },
        datasets: [],
        termination: null,
      }),
    );

    expect(answer.footnote).toBe("1 decision, 1 experiment, 1 evidence item.");
  });

  it("carries each claim with the status and confidence the run left it at", () => {
    const answer = composeAnswer(
      detail({
        hypotheses: [
          { id: "h-a", statement: "staffing drives it", status: "weakened", confidence: 0.5 } as never,
          { id: "h-b", statement: "volume drives it", status: "supported", confidence: 0.95 } as never,
        ],
      }),
    );

    expect(answer.claims).toEqual([
      { id: "h-a", statement: "staffing drives it", status: "weakened", confidence: 0.5 },
      { id: "h-b", statement: "volume drives it", status: "supported", confidence: 0.95 },
    ]);
  });

  it("prefers the structured conclusion over the summary string", () => {
    const answer = composeAnswer(
      detail({
        conclusion: "summary line",
        conclusion_detail: { statement: "the full conclusion" } as never,
      }),
    );

    expect(answer.conclusion).toBe("the full conclusion");
  });

  it("falls back to the summary string when there is no structured conclusion", () => {
    const answer = composeAnswer(detail({ conclusion: "summary line" }));

    expect(answer.conclusion).toBe("summary line");
  });

  it("reports no conclusion rather than inventing one", () => {
    // A run that reached no conclusion must not be given a sentence that reads like one.
    const answer = composeAnswer(detail({ conclusion: null, conclusion_detail: null }));

    expect(answer.conclusion).toBeNull();
  });

  it("surfaces the questions the run left open", () => {
    const answer = composeAnswer(
      detail({
        open_questions: [
          { id: "q1", question: "is it stable over time?" } as never,
          { id: "q2", question: "which of the two holds?" } as never,
        ],
      }),
    );

    expect(answer.openQuestions).toEqual(["is it stable over time?", "which of the two holds?"]);
  });

  it("produces an answer for a run with nothing in it, without throwing", () => {
    const answer = composeAnswer(
      detail({
        counts: {
          hypotheses: 0, evidence: 0, experiments: 0, observations: 0,
          decisions: 0, critiques: 0, open_questions: 0,
        },
        outcome: { ...detail().outcome, kind: "declined", contradiction_found: false },
        datasets: [],
        termination: null,
      }),
    );

    expect(answer.claims).toEqual([]);
    expect(answer.openQuestions).toEqual([]);
    expect(answer.headline).toBeTruthy();
    expect(answer.footnote).toBe("0 decisions, 0 experiments, 0 evidence items.");
  });
});
