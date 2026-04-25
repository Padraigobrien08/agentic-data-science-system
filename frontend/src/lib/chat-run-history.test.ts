import { describe, expect, it, vi } from "vitest";

const { listRunsMock, getRunMock, listRunArtifactsMock } = vi.hoisted(() => ({
  listRunsMock: vi.fn(),
  getRunMock: vi.fn(),
  listRunArtifactsMock: vi.fn(),
}));

vi.mock("@/lib/api/runs", () => ({
  listRuns: listRunsMock,
  getRun: getRunMock,
  listRunArtifacts: listRunArtifactsMock,
}));

import { buildProjectChatHistory } from "@/lib/chat-run-history";

describe("buildProjectChatHistory", () => {
  it("maps persisted runs into an oldest-to-newest transcript with answer cards", async () => {
    listRunsMock.mockResolvedValue([
      {
        id: "run-2",
        project_id: "project-1",
        initiated_by_user_id: "user-1",
        correlation_id: null,
        status: "success",
        orchestration_goal_text: "Compare AAPL and MSFT on operating margin",
        error_summary: null,
        started_at: "2026-04-19T10:01:00Z",
        finished_at: "2026-04-19T10:02:00Z",
        created_at: "2026-04-19T10:00:00Z",
        updated_at: "2026-04-19T10:02:00Z",
        current_phase: "finished",
        total_steps: 5,
        completed_steps: 5,
      },
      {
        id: "run-1",
        project_id: "project-1",
        initiated_by_user_id: "user-1",
        correlation_id: null,
        status: "success",
        orchestration_goal_text: "Assess whether margin pressure is temporary or structural for MSFT",
        error_summary: null,
        started_at: "2026-04-19T09:01:00Z",
        finished_at: "2026-04-19T09:02:00Z",
        created_at: "2026-04-19T09:00:00Z",
        updated_at: "2026-04-19T09:02:00Z",
        current_phase: "finished",
        total_steps: 5,
        completed_steps: 5,
      },
    ]);
    getRunMock.mockImplementation(async (runId: string) => ({
      id: runId,
      project_id: "project-1",
      initiated_by_user_id: "user-1",
      correlation_id: null,
      status: "success",
      orchestration_goal_text:
        runId === "run-1"
          ? "Assess whether margin pressure is temporary or structural for MSFT"
          : "Compare AAPL and MSFT on operating margin",
      error_summary: null,
      started_at: runId === "run-1" ? "2026-04-19T09:01:00Z" : "2026-04-19T10:01:00Z",
      finished_at: runId === "run-1" ? "2026-04-19T09:02:00Z" : "2026-04-19T10:02:00Z",
      created_at: runId === "run-1" ? "2026-04-19T09:00:00Z" : "2026-04-19T10:00:00Z",
      updated_at: runId === "run-1" ? "2026-04-19T09:02:00Z" : "2026-04-19T10:02:00Z",
      current_phase: "finished",
      total_steps: 5,
      completed_steps: 5,
      input_payload_json: {
        tickers: runId === "run-1" ? ["MSFT"] : ["AAPL", "MSFT"],
        analysis_goal:
          runId === "run-1"
            ? "Assess whether margin pressure is temporary or structural for MSFT"
            : "Compare AAPL and MSFT on operating margin",
      },
      output_payload_json: {
        status: "success",
        final_summary:
          runId === "run-1"
            ? "MSFT margin pressure looks cyclical rather than structural."
            : "MSFT is lagging AAPL on operating margin stability.",
      },
      meta_json: null,
      transparency: null,
    }));
    listRunArtifactsMock.mockImplementation(async (runId: string) => [
      {
        id: `report-${runId}`,
        analysis_run_id: runId,
        evaluation_run_id: null,
        run_step_id: null,
        role_key: "report_md",
        kind: "document",
        mime_type: "text/markdown",
        byte_size: 100,
        content_sha256: null,
        storage_uri: `local://report-${runId}`,
        created_at: "2026-04-19T09:02:00Z",
        updated_at: "2026-04-19T09:02:00Z",
      },
    ]);

    const result = await buildProjectChatHistory("project-1");

    expect(result.messages).toHaveLength(4);
    expect(result.messages[0]).toMatchObject({
      role: "user",
      content: "Assess whether margin pressure is temporary or structural for MSFT",
    });
    expect(result.messages[1]).toMatchObject({
      role: "assistant",
      content: "MSFT margin pressure looks cyclical rather than structural.",
      runHref: "/projects/project-1/runs/run-1/trace",
      answerCard: {
        narrativeAnswer: {
          mode: "legacy",
          thesis: "MSFT margin pressure looks cyclical rather than structural.",
          fallbackReason: "legacy_summary",
        },
        summaryLine: "MSFT margin pressure looks cyclical rather than structural.",
        navigationItems: expect.arrayContaining([
          expect.objectContaining({ key: "report", href: "/artifacts/report-run-1" }),
        ]),
      },
    });
    expect(result.recentRuns).toHaveLength(2);
    expect(result.recentRuns[0]).toMatchObject({
      id: "run-2",
      title: "MSFT is lagging AAPL on operating margin stability.",
      scrollTargetId: "answer-run-2",
    });
  });
});
