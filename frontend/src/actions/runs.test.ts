import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  revalidatePathMock,
  redirectMock,
  createRunMock,
  executeRunMock,
  getPromptRoutingPreviewMock,
  getRunMock,
  listRunArtifactsMock,
} = vi.hoisted(() => ({
  revalidatePathMock: vi.fn(),
  redirectMock: vi.fn(),
  createRunMock: vi.fn(),
  executeRunMock: vi.fn(),
  getPromptRoutingPreviewMock: vi.fn(),
  getRunMock: vi.fn(),
  listRunArtifactsMock: vi.fn(),
}));

vi.mock("next/cache", () => ({
  revalidatePath: revalidatePathMock,
}));

vi.mock("next/navigation", () => ({
  redirect: redirectMock,
}));

vi.mock("@/lib/api/runs", () => ({
  createRun: createRunMock,
  executeRun: executeRunMock,
  getPromptRoutingPreview: getPromptRoutingPreviewMock,
  getRun: getRunMock,
  listRunArtifacts: listRunArtifactsMock,
}));

import { createAnalysisRunFromChat } from "@/actions/runs";

function buildFormData(overrides?: { goal?: string; requestId?: string; tickers?: string; refresh?: boolean }) {
  const formData = new FormData();
  formData.set("goal", overrides?.goal ?? "Analyze margin pressure for AAPL versus MSFT");
  formData.set("request_id", overrides?.requestId ?? "req-1");
  formData.set("tickers", overrides?.tickers ?? "AAPL,MSFT");
  if (overrides?.refresh) {
    formData.set("refresh", "on");
  }
  return formData;
}

describe("createAnalysisRunFromChat", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("returns rewriteSuggestions for unsupported previews without creating or executing a run", async () => {
    getPromptRoutingPreviewMock.mockResolvedValue({
      supported: false,
      routing_source: "deterministic",
      reason: "TSLA is outside the current workspace scope.",
      rewrite_suggestions: [
        "Compare AAPL and MSFT on operating margin over the last eight quarters.",
        "Assess whether margin pressure is temporary or structural for MSFT.",
      ],
      effective_tickers: ["AAPL", "MSFT"],
    });

    const result = await createAnalysisRunFromChat("project-1", {}, buildFormData());

    expect(result).toMatchObject({
      reply: {
        requestId: "req-1",
        content: "I couldn't route that request yet.",
        rewriteSuggestions: [
          "Compare AAPL and MSFT on operating margin over the last eight quarters.",
          "Assess whether margin pressure is temporary or structural for MSFT.",
        ],
        routingReason: "TSLA is outside the current workspace scope.",
      },
    });
    expect(result.reply?.runId).toBeUndefined();
    expect(result.reply?.runHref).toBeUndefined();
    expect(result.reply?.deepDiveHref).toBeUndefined();
    expect(result.reply?.runsHref).toBeUndefined();
    expect(createRunMock).not.toHaveBeenCalled();
    expect(executeRunMock).not.toHaveBeenCalled();
    expect(revalidatePathMock).not.toHaveBeenCalled();
  });

  it("creates and executes a run with preview effective_tickers when routing is supported", async () => {
    getPromptRoutingPreviewMock.mockResolvedValue({
      supported: true,
      routing_source: "deterministic",
      effective_tickers: ["MSFT"],
      reason: null,
      rewrite_suggestions: [],
      goal_code: "trend_deterioration",
      intent: "anomaly_analysis",
      plan_template_id: "trend-deterioration",
    });
    createRunMock.mockResolvedValue({ id: "run-1" });
    executeRunMock.mockResolvedValue({
      analysis_run_id: "run-1",
      orchestration_run_id: "orch-1",
      orchestration_status: "success",
      message: "ok",
      final_summary: "done",
      artifact_count: 1,
      db_status: "success",
    });
    getRunMock.mockResolvedValue({
      id: "run-1",
      project_id: "project-1",
      initiated_by_user_id: "user-1",
      correlation_id: null,
      status: "success",
      orchestration_goal_text: "Assess whether margin pressure is temporary or structural for MSFT",
      error_summary: null,
      started_at: "2026-04-19T12:01:00Z",
      finished_at: "2026-04-19T12:02:00Z",
      created_at: "2026-04-19T12:00:00Z",
      updated_at: "2026-04-19T12:02:00Z",
      current_phase: "finished",
      total_steps: 5,
      completed_steps: 5,
      input_payload_json: {
        tickers: ["MSFT"],
        analysis_goal: "Assess whether margin pressure is temporary or structural for MSFT",
        refresh: true,
      },
      output_payload_json: {
        status: "success",
        final_summary: "MSFT margin pressure looks cyclical rather than structural.",
      },
      meta_json: null,
      transparency: null,
    });
    listRunArtifactsMock.mockResolvedValue([
      {
        id: "report-1",
        analysis_run_id: "run-1",
        evaluation_run_id: null,
        run_step_id: null,
        role_key: "report_md",
        kind: "document",
        mime_type: "text/markdown",
        byte_size: 100,
        content_sha256: null,
        storage_uri: "local://report-1",
        created_at: "2026-04-19T12:02:00Z",
        updated_at: "2026-04-19T12:02:00Z",
      },
    ]);

    const result = await createAnalysisRunFromChat(
      "project-1",
      {},
      buildFormData({
        goal: "Assess whether margin pressure is temporary or structural for MSFT",
        tickers: "AAPL,MSFT,NVDA",
        refresh: true,
      }),
    );

    expect(getPromptRoutingPreviewMock).toHaveBeenCalledWith({
      project_id: "project-1",
      analysis_goal: "Assess whether margin pressure is temporary or structural for MSFT",
      tickers: ["AAPL", "MSFT", "NVDA"],
      refresh: true,
    });
    expect(createRunMock).toHaveBeenCalledWith({
      project_id: "project-1",
      orchestration_goal_text: "Assess whether margin pressure is temporary or structural for MSFT",
      input_payload_json: {
        tickers: ["MSFT"],
        analysis_goal: "Assess whether margin pressure is temporary or structural for MSFT",
        refresh: true,
      },
      enqueue_execution: false,
    });
    expect(executeRunMock).toHaveBeenCalledWith("run-1", {});
    expect(getRunMock).toHaveBeenCalledWith("run-1", { includeTransparency: true });
    expect(listRunArtifactsMock).toHaveBeenCalledWith("run-1");
    expect(result.reply).toMatchObject({
      requestId: "req-1",
      runId: "run-1",
      runHref: "/projects/project-1/runs/run-1",
      runStatus: "success",
      runCreatedAt: "2026-04-19T12:00:00Z",
      runFinishedAt: "2026-04-19T12:02:00Z",
      answerCard: {
        goalDisplay: "Assess whether margin pressure is temporary or structural for MSFT",
        summaryLine: "MSFT margin pressure looks cyclical rather than structural.",
        orchestrationStatus: "success",
        conclusionRider: null,
        takeawayRows: [],
        navigationItems: expect.arrayContaining([
          expect.objectContaining({ key: "report", href: "/artifacts/report-1" }),
          expect.objectContaining({ key: "trace", href: "/projects/project-1/runs/run-1/trace" }),
        ]),
        caveatOverflowHref: "/projects/project-1/runs/run-1/trace#run-context-transparency",
      },
    });
  });
});
