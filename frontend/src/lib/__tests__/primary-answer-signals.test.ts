import { describe, expect, it } from "vitest";

import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";

import { collectContextSignals, extractWeakEvidenceSignals } from "../primary-answer-signals";

describe("extractWeakEvidenceSignals", () => {
  it("reads critic phase_output", () => {
    const ai: ParsedAiAgents = {
      critic: {
        phase_output: { weak_evidence_signals: ["flagged_issues", "low_overall_confidence"] },
      },
    };
    expect(extractWeakEvidenceSignals(ai)).toEqual(["flagged_issues", "low_overall_confidence"]);
  });

  it("returns empty when missing", () => {
    expect(extractWeakEvidenceSignals(null)).toEqual([]);
  });
});

describe("collectContextSignals", () => {
  it("flags llm_context_budget_applied on critic audit", () => {
    const ai: ParsedAiAgents = {
      critic: { llm_context_audit: { llm_context_budget_applied: true } },
    };
    const out = collectContextSignals(ai, null);
    expect(out.some((s) => s.id === "llm_context_budget")).toBe(true);
  });

  it("dedupes same audit flag from critic and report", () => {
    const audit = { llm_context_budget_applied: true };
    const ai: ParsedAiAgents = {
      critic: { llm_context_audit: audit },
      report: { llm_context_audit: audit },
    };
    expect(collectContextSignals(ai, null).filter((s) => s.id === "llm_context_budget")).toHaveLength(1);
  });

  it("includes orchestration degraded when present", () => {
    const orch: ParsedOrchestrationOutput = {
      llm_phases_summary: { critic: { degraded: true } },
    };
    const out = collectContextSignals(null, orch);
    expect(out.some((s) => s.id === "lps_critic_degraded")).toBe(true);
  });
});
