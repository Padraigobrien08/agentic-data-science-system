import { describe, expect, it } from "vitest";

import type { ParsedAiAgents } from "@/lib/ai-agents-meta";
import type { ParsedOrchestrationOutput } from "@/lib/orchestration-output";

import {
  collectContextSignals,
  contextReliabilityFootnote,
  extractWeakEvidenceSignals,
} from "../primary-answer-signals";

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
    expect(out.some((s) => s.id === "lcb_llm_context_budget_applied")).toBe(true);
  });

  it("expands nested llm_context_budget keys when present", () => {
    const ai: ParsedAiAgents = {
      critic: {
        llm_context_audit: {
          llm_context_budget: { user_request_truncated: true, warnings_sample_truncated: true },
        },
      },
    };
    const out = collectContextSignals(ai, null);
    expect(out.some((s) => s.id === "lcb_user_request_truncated")).toBe(true);
    expect(out.some((s) => s.id === "lcb_warnings_sample_truncated")).toBe(true);
  });

  it("dedupes same audit flag from critic and report", () => {
    const audit = { llm_context_budget_applied: true };
    const ai: ParsedAiAgents = {
      critic: { llm_context_audit: audit },
      report: { llm_context_audit: audit },
    };
    expect(
      collectContextSignals(ai, null).filter((s) => s.id === "lcb_llm_context_budget_applied"),
    ).toHaveLength(1);
  });

  it("includes orchestration degraded when present", () => {
    const orch: ParsedOrchestrationOutput = {
      llm_phases_summary: { critic: { degraded: true } },
    };
    const out = collectContextSignals(null, orch);
    expect(out.some((s) => s.id === "lps_critic_degraded")).toBe(true);
  });

  it("surfaces orchestration warning count", () => {
    const orch: ParsedOrchestrationOutput = { warnings: [{}, {}] as unknown[] };
    const out = collectContextSignals(null, orch);
    expect(out.some((s) => s.id === "orch_warnings")).toBe(true);
  });
});

describe("contextReliabilityFootnote", () => {
  it("returns null when nothing notable", () => {
    expect(contextReliabilityFootnote([], [])).toBeNull();
  });

  it("mentions weak evidence", () => {
    const s = contextReliabilityFootnote([], ["thin_panel"]);
    expect(s).toContain("Weak-evidence");
  });
});
