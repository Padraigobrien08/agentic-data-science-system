import { describe, expect, it } from "vitest";

import { parseLlmContextAuditRows, parseLlmContextBudgetDict } from "../context-transparency";

describe("parseLlmContextBudgetDict", () => {
  it("maps true keys to rows", () => {
    const rows = parseLlmContextBudgetDict({
      user_request_truncated: true,
      errors_sample_truncated: true,
    });
    expect(rows.map((r) => r.key).sort()).toEqual(["errors_sample_truncated", "user_request_truncated"]);
  });
});

describe("parseLlmContextAuditRows", () => {
  it("prefers granular dict over umbrella flags", () => {
    const rows = parseLlmContextAuditRows({
      llm_context_budget: { plan_alignment_findings_truncated: true },
      llm_context_budget_applied: true,
    });
    expect(rows.some((r) => r.key === "plan_alignment_findings_truncated")).toBe(true);
    expect(rows.some((r) => r.key === "llm_context_budget_applied")).toBe(false);
  });

  it("falls back to umbrella when no granular keys", () => {
    const rows = parseLlmContextAuditRows({
      llm_context_budget_applied: true,
      context_budget_truncated: true,
    });
    expect(rows.map((r) => r.key)).toContain("llm_context_budget_applied");
    expect(rows.map((r) => r.key)).toContain("context_budget_truncated");
  });
});
