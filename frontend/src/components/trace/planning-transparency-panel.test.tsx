import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PlanningTransparencyPanel } from "./planning-transparency-panel";

describe("PlanningTransparencyPanel", () => {
  it("renders rule-derived rationale and typed preference fields (no raw JSON dump)", () => {
    const transparency = {
      contract_version: "1",
      present: true,
      planning_rationale_summary:
        "Classified the request as «trend_deterioration» using deterministic rules on the goal text.",
      plan_template_id: "trend_deterioration",
      orchestration_intent: "anomaly_analysis",
      goal_code: "trend_deterioration",
      primary_analysis_mode: "deterioration",
      priority_metrics: ["margins", "cash_flow"],
      directional_focus: "negative",
      preferred_signal_style: "persistent",
      peer_requirement: "optional",
      time_focus: "recent_quarters",
      emphasized: ["Sustained multi-period patterns"],
      deemphasized: ["One-quarter-only anomaly reads unless extreme."],
    };

    render(<PlanningTransparencyPanel transparency={transparency} />);

    expect(screen.getByText(/Planning rationale \(rule-derived\)/i)).toBeInstanceOf(
      HTMLElement,
    );
    expect(
      screen.getByText(/Classified the request as «trend_deterioration»/),
    ).toBeInstanceOf(HTMLElement);
    expect(screen.getByText(/orchestration_intent \(coarse\)/i)).toBeInstanceOf(HTMLElement);
    expect(screen.getByText(/anomaly_analysis/)).toBeInstanceOf(HTMLElement);
    expect(screen.getByText(/signal: persistent/i)).toBeInstanceOf(HTMLElement);
    expect(screen.getByText(/direction: negative/i)).toBeInstanceOf(HTMLElement);
    expect(screen.getByText(/margins, cash_flow/)).toBeInstanceOf(HTMLElement);
    expect(screen.getByText(/Prioritized/i)).toBeInstanceOf(HTMLElement);
  });

  it("shows absent state when transparency is missing", () => {
    render(<PlanningTransparencyPanel transparency={null} />);
    expect(screen.getByText(/No structured planning transparency/i)).toBeInstanceOf(
      HTMLElement,
    );
  });
});
