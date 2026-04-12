import { describe, expect, it } from "vitest";

import type { RunStepDetail } from "@/lib/api/types";
import {
  classifyStepToPhaseIndex,
  deriveCurrentPhaseIndex,
  derivePipelinePhaseView,
} from "@/lib/run-pipeline-phases";

function baseStep(overrides: Partial<RunStepDetail> & Pick<RunStepDetail, "step_index" | "status">): RunStepDetail {
  return {
    id: "00000000-0000-4000-8000-000000000001",
    analysis_run_id: "00000000-0000-4000-8000-000000000002",
    step_index: overrides.step_index,
    status: overrides.status,
    label: overrides.label ?? null,
    planned_tool_name: overrides.planned_tool_name ?? null,
    detail: overrides.detail ?? null,
    started_at: overrides.started_at ?? null,
    finished_at: overrides.finished_at ?? null,
    created_at: "2020-01-01T00:00:00Z",
    updated_at: "2020-01-01T00:00:00Z",
    planner_tool_input_json: overrides.planner_tool_input_json ?? null,
    meta_json: overrides.meta_json ?? null,
    transparency: overrides.transparency ?? null,
  };
}

describe("classifyStepToPhaseIndex", () => {
  it("maps mcp_executor to panels phase", () => {
    const s = baseStep({
      step_index: 0,
      status: "running",
      meta_json: { trace: "mcp_executor" },
    });
    expect(classifyStepToPhaseIndex(s)).toBe(1);
  });

  it("maps critic_agent to review phase", () => {
    const s = baseStep({
      step_index: 3,
      status: "running",
      meta_json: { trace: "critic_agent", phase: "llm" },
    });
    expect(classifyStepToPhaseIndex(s)).toBe(3);
  });

  it("maps report_agent to report phase", () => {
    const s = baseStep({
      step_index: 4,
      status: "pending",
      meta_json: { trace: "report_agent", phase: "llm" },
    });
    expect(classifyStepToPhaseIndex(s)).toBe(4);
  });
});

describe("deriveCurrentPhaseIndex", () => {
  it("uses pending / queued at phase 0", () => {
    expect(deriveCurrentPhaseIndex("pending", [])).toBe(0);
    expect(deriveCurrentPhaseIndex("queued", [])).toBe(0);
  });

  it("uses first active step phase when running", () => {
    const steps = [
      baseStep({
        step_index: 0,
        status: "success",
        meta_json: { trace: "mcp_executor" },
      }),
      baseStep({
        step_index: 1,
        status: "running",
        meta_json: { trace: "mcp_executor" },
      }),
    ];
    expect(deriveCurrentPhaseIndex("running", steps)).toBe(1);
  });

  it("treats terminal success as final phase", () => {
    expect(deriveCurrentPhaseIndex("success", [])).toBe(4);
  });
});

describe("derivePipelinePhaseView", () => {
  it("marks prior phases done when MCP is running", () => {
    const steps = [
      baseStep({
        step_index: 0,
        status: "success",
        meta_json: { trace: "mcp_executor" },
      }),
      baseStep({
        step_index: 1,
        status: "running",
        meta_json: { trace: "mcp_executor" },
      }),
    ];
    const v = derivePipelinePhaseView("running", steps);
    expect(v.lines[0].state).toBe("done");
    expect(v.lines[1].state).toBe("current");
    expect(v.lines[2].state).toBe("upcoming");
    expect(v.headline).toContain("Building panels");
  });

  it("marks all phases done on success", () => {
    const v = derivePipelinePhaseView("success", []);
    expect(v.lines.every((l) => l.state === "done")).toBe(true);
  });
});
