import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { RunTraceSummaryView } from "@/components/trace/run-trace-summary-view";
import type { RunTraceRawDetail, RunTraceShell } from "@/lib/api/types";

const shell: RunTraceShell = {
  run: {
    id: "run-1",
    project_id: "project-1",
    initiated_by_user_id: "user-1",
    correlation_id: null,
    status: "success",
    orchestration_goal_text: "Compare operating margin durability across peers.",
    error_summary: null,
    started_at: "2026-04-18T12:00:00Z",
    finished_at: "2026-04-18T12:05:00Z",
    created_at: "2026-04-18T12:00:00Z",
    updated_at: "2026-04-18T12:05:00Z",
    current_phase: "report",
    total_steps: 3,
    completed_steps: 3,
  },
  transparency: {
    evidence_artifact_ids: ["artifact-1"],
    evidence_artifacts_by_role: { report_md: "artifact-1" },
    prompt_versions: { report: "1.0.0" },
    model_call_count: 2,
  },
  timeline_preview: [
    {
      id: "step-1",
      analysis_run_id: "run-1",
      step_index: 0,
      status: "success",
      label: "panel load",
      planned_tool_name: "load_panel",
      detail: "Load peer comparison panels",
      started_at: "2026-04-18T12:00:00Z",
      finished_at: "2026-04-18T12:01:00Z",
      created_at: "2026-04-18T12:00:00Z",
      updated_at: "2026-04-18T12:01:00Z",
      planner_tool_input_json: null,
      meta_json: null,
      transparency: {
        trace: "mcp_executor",
        phase: "plan",
        model_call_id: null,
        output_summary: null,
        linked_artifact_ids: [],
      },
    },
  ],
  steps: {
    total: 3,
    limit: 5,
    has_more: false,
    items: [],
  },
  artifacts: {
    total: 2,
    limit: 4,
    has_more: false,
    items: [],
  },
  model_calls: {
    total: 2,
    limit: 4,
    has_more: false,
    items: [],
  },
};

describe("RunTraceSummaryView", () => {
  it("renders overview-first content and separate collection labels", () => {
    render(
      <RunTraceSummaryView
        projectId="project-1"
        runId="run-1"
        shell={shell}
        activeCollection="steps"
        runAnswerHref="/projects/project-1/runs/run-1"
        collectionPanel={{
          projectId: "project-1",
          runId: "run-1",
          collection: "steps",
          items: shell.timeline_preview,
          limit: 5,
          offset: 0,
          hasMore: false,
        }}
      />,
    );

    expect(screen.getByText(/Audit the run without loading every raw blob first/i)).toBeTruthy();
    expect(screen.getByText("The step spine stays primary")).toBeTruthy();
    expect(screen.getByRole("link", { name: "View all steps" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open artifact preview" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Inspect model call" })).toBeTruthy();
    expect(screen.getAllByText("Inspect step details").length).toBeGreaterThan(0);
  });

  it("renders the approved error and empty-state copy", () => {
    render(
      <RunTraceSummaryView
        projectId="project-1"
        runId="run-1"
        shell={{
          ...shell,
          steps: { ...shell.steps, total: 0 },
          artifacts: { ...shell.artifacts, total: 0 },
          model_calls: { ...shell.model_calls, total: 0 },
          timeline_preview: [],
        }}
        activeCollection="steps"
        runAnswerHref="/projects/project-1/runs/run-1"
        collectionPanel={{
          projectId: "project-1",
          runId: "run-1",
          collection: "steps",
          items: [],
          limit: 5,
          offset: 0,
          hasMore: false,
        }}
        errorMessage="backend timed out"
      />,
    );

    expect(screen.getAllByText("No trace details yet").length).toBeGreaterThan(0);
    expect(screen.getByText("Trace details couldn't load.")).toBeTruthy();
  });

  it("keeps the overview visible while one selected raw detail surface is open", () => {
    const rawDetail: RunTraceRawDetail = {
      kind: "step",
      selectedId: "step-1",
      item: shell.timeline_preview[0],
      closeHref: "/projects/project-1/runs/run-1/trace?collection=steps#trace-collection",
    };

    render(
      <RunTraceSummaryView
        projectId="project-1"
        runId="run-1"
        shell={shell}
        activeCollection="steps"
        runAnswerHref="/projects/project-1/runs/run-1"
        rawDetail={rawDetail}
        collectionPanel={{
          projectId: "project-1",
          runId: "run-1",
          collection: "steps",
          items: shell.timeline_preview,
          limit: 5,
          offset: 0,
          hasMore: false,
          selectedId: "step-1",
        }}
      />,
    );

    expect(screen.getByText(/Audit the run without loading every raw blob first/i)).toBeTruthy();
    expect(screen.getByText("The step spine stays primary")).toBeTruthy();
    expect(screen.getAllByText("Open raw payload").length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: "Close" }).length).toBeGreaterThan(0);
  });
});
