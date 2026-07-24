import { describe, expect, it } from "vitest";

import type { HypothesisItem, InvestigationDetail } from "@/lib/api/types";
import {
  confidenceDelta,
  dispositionTone,
  evidenceForHypothesis,
  formatConfidence,
  hypothesisStatusTone,
  investigationStatusTone,
  titleize,
} from "@/lib/investigation-view";

function hyp(overrides: Partial<HypothesisItem> = {}): HypothesisItem {
  return {
    id: "h1",
    statement: "revenue rising",
    status: "supported",
    confidence: 0.9,
    prior_confidence: 0.5,
    rationale: null,
    metric_refs: [],
    entity_refs: [],
    ...overrides,
  };
}

describe("investigation-view helpers", () => {
  it("formats confidence as whole percent and clamps", () => {
    expect(formatConfidence(0.951)).toBe("95%");
    expect(formatConfidence(0)).toBe("0%");
    expect(formatConfidence(1.4)).toBe("100%");
    expect(formatConfidence(null)).toBe("—");
    expect(formatConfidence(undefined)).toBe("—");
  });

  it("maps statuses and dispositions to stable labels", () => {
    expect(investigationStatusTone("converged").label).toBe("Converged");
    expect(investigationStatusTone("exhausted").label).toBe("Exhausted");
    expect(hypothesisStatusTone("rejected").label).toBe("Rejected");
    expect(dispositionTone("insufficient_evidence").label).toBe("Insufficient evidence");
    expect(dispositionTone("inconclusive").label).toBe("Inconclusive");
  });

  it("titleizes snake_case decision types", () => {
    expect(titleize("select_experiment")).toBe("Select Experiment");
    expect(titleize("propose_hypothesis")).toBe("Propose Hypothesis");
  });

  it("computes confidence delta, null when unchanged", () => {
    expect(confidenceDelta(hyp({ confidence: 0.9, prior_confidence: 0.5 }))).toBeCloseTo(0.4);
    expect(confidenceDelta(hyp({ confidence: 0.5, prior_confidence: 0.5 }))).toBeNull();
  });

  it("links evidence to a hypothesis by id", () => {
    const detail = {
      evidence: [
        { id: "e1", hypothesis_ids: ["h1"], claim: "", evidence_type: "", direction: "supports", strength: 0.8, reliability: 0.8, coverage: 0.8, experiment_result_id: null, statistics: null },
        { id: "e2", hypothesis_ids: ["h2"], claim: "", evidence_type: "", direction: "refutes", strength: 0.5, reliability: 0.5, coverage: 0.5, experiment_result_id: null, statistics: null },
      ],
    } as unknown as InvestigationDetail;
    const linked = evidenceForHypothesis(detail, hyp({ id: "h1" }));
    expect(linked.map((e) => e.id)).toEqual(["e1"]);
  });
});
