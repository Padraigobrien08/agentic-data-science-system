import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { StepStatusTimeline } from "@/components/transparency/step-status-timeline";
import type { RunStepDetail } from "@/lib/api/types";

describe("StepStatusTimeline", () => {
  it("renders structured output_summary from API transparency without raw meta_json", () => {
    const steps: RunStepDetail[] = [
      {
        id: "step-1",
        analysis_run_id: "run-1",
        step_index: 0,
        status: "success",
        label: "critic_agent",
        planned_tool_name: null,
        detail: null,
        started_at: null,
        finished_at: null,
        created_at: "2020-01-01T00:00:00Z",
        updated_at: "2020-01-01T00:00:00Z",
        planner_tool_input_json: null,
        meta_json: { trace: "critic_agent", phase_output: { buried: true } },
        transparency: {
          trace: "critic_agent",
          phase: "llm",
          model_call_id: null,
          output_summary: {
            phase_status: "degraded",
            skipped: null,
            skip_reason: null,
            issue_count: 2,
            overall_confidence: "low",
            key_takeaway_count: null,
            markdown_char_count: null,
            step_count: null,
            artifact_roles: [],
            weak_evidence_signals: ["flagged_issues"],
          },
          linked_artifact_ids: ["aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"],
        },
      },
    ];
    render(
      <StepStatusTimeline
        steps={steps}
        modelCallById={new Map()}
        projectId="p1"
        runId="r1"
      />,
    );
    expect(screen.getByText(/phase_status: degraded/)).toBeTruthy();
    expect(screen.getByText(/issue_count: 2/)).toBeTruthy();
    expect(screen.getByText(/weak_evidence_signals: flagged_issues/)).toBeTruthy();
    expect(screen.getByText(/phase:llm/)).toBeTruthy();
    const artLink = screen.getByRole("link", { name: /aaaaaaa/ });
    expect(artLink.getAttribute("href")).toBe(
      "/artifacts/aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee",
    );
  });
});
