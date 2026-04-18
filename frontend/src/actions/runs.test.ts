import { beforeEach, describe, expect, it, vi } from "vitest";

const {
  revalidatePathMock,
  redirectMock,
  createRunMock,
  executeRunMock,
  getPromptRoutingPreviewMock,
} = vi.hoisted(() => ({
  revalidatePathMock: vi.fn(),
  redirectMock: vi.fn(),
  createRunMock: vi.fn(),
  executeRunMock: vi.fn(),
  getPromptRoutingPreviewMock: vi.fn(),
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
    expect(result.reply).toMatchObject({
      requestId: "req-1",
      runId: "run-1",
      runHref: "/projects/project-1/runs/run-1",
      deepDiveHref: "/projects/project-1/runs/run-1/trace",
      runsHref: "/projects/project-1/runs",
    });
  });
});
