import { describe, expect, it } from "vitest";

import {
  buildOutcomeSuggestions,
  classifyGoalArchetype,
  hasContextBudgetSignal,
} from "@/lib/run-outcome-suggestions";
import type { PrimaryContextSignal } from "@/lib/primary-answer-signals";

describe("classifyGoalArchetype", () => {
  it("detects peer-style goals", () => {
    expect(classifyGoalArchetype("Benchmark vs peers in industry", [])).toBe("peer_compare");
  });

  it("detects time-style goals", () => {
    expect(classifyGoalArchetype("FY22 to FY24 revenue trend", [])).toBe("time_series");
  });

  it("detects risk-style goals before peer keywords", () => {
    expect(classifyGoalArchetype("Red flags and covenant risk vs peers", [])).toBe("risk_signal");
  });

  it("falls back to general", () => {
    expect(classifyGoalArchetype("Tell me about the company", [])).toBe("general");
  });
});

describe("buildOutcomeSuggestions", () => {
  const trace = "/projects/p/runs/r1/trace";
  const emptySignals: PrimaryContextSignal[] = [];

  it("returns null for success", () => {
    expect(buildOutcomeSuggestions("success", "g", [], emptySignals, 0, "p", trace)).toBeNull();
  });

  it("returns three partial_success actions", () => {
    const out = buildOutcomeSuggestions("partial_success", "general goal", [], emptySignals, 0, "p", trace);
    expect(out).toHaveLength(3);
    expect(out![0]!.href).toContain("#run-agents");
    expect(out![2]!.href).toBe("/projects/p/runs/new");
  });

  it("prioritizes budget hint in middle slot for partial_success", () => {
    const signals: PrimaryContextSignal[] = [
      { id: "llm_context_budget", label: "Context limits", tone: "warning", tooltip: "trimmed" },
    ];
    const out = buildOutcomeSuggestions("partial_success", "goal", [], signals, 0, "p", trace);
    expect(out![1]!.title).toContain("scope");
    expect(out![1]!.href).toContain("#run-context-transparency");
  });

  it("returns three no_data actions with chat on last step", () => {
    const out = buildOutcomeSuggestions("no_data", "Compare AAPL MSFT", ["AAPL", "MSFT"], emptySignals, 0, "p", trace);
    expect(out).toHaveLength(3);
    expect(out![0]!.href).toContain("#run-execution");
    expect(out![2]!.href).toBe("/projects/p/chat");
  });
});

describe("hasContextBudgetSignal", () => {
  it("detects llm_context_budget id", () => {
    expect(
      hasContextBudgetSignal([{ id: "llm_context_budget", label: "x", tone: "warning" }]),
    ).toBe(true);
  });
});
