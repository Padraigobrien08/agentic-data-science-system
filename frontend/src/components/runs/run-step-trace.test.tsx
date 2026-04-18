import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunStepTrace } from "@/components/runs/run-step-trace";
import type { RunStepDetail } from "@/lib/api/types";

const step: RunStepDetail = {
  id: "step-1",
  analysis_run_id: "run-1",
  step_index: 0,
  status: "success",
  label: "Load peer panel",
  planned_tool_name: "load_panel",
  detail: "Collect the persisted comparison table.",
  started_at: "2026-04-18T12:00:00Z",
  finished_at: "2026-04-18T12:01:00Z",
  created_at: "2026-04-18T12:00:00Z",
  updated_at: "2026-04-18T12:01:00Z",
  planner_tool_input_json: { ticker: "AAPL" },
  meta_json: { trace: "mcp_executor", phase: "plan" },
  transparency: {
    trace: "mcp_executor",
    phase: "plan",
    model_call_id: null,
    output_summary: null,
    linked_artifact_ids: [],
  },
};

describe("RunStepTrace", () => {
  it("keeps raw JSON hidden by default and links step inspection back to the summary-first trace page", () => {
    render(<RunStepTrace projectId="project-1" runId="run-1" steps={[step]} />);

    const inspectLink = screen.getByRole("link", { name: "Inspect step details" });
    expect(inspectLink.getAttribute("href")).toBe(
      "/projects/project-1/runs/run-1/trace?collection=steps&focus=step-1#trace-collection",
    );
    expect(screen.getByText(/Open raw payload from the summary-first trace view/i)).toBeTruthy();
    expect(screen.queryByText(/planner_tool_input_json/i)).toBeNull();
    expect(screen.queryByText(/Step meta \(RunStep\.meta_json\)/i)).toBeNull();
    expect(screen.queryByText("AAPL")).toBeNull();
  });
});
