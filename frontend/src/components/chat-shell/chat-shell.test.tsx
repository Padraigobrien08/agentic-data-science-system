import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell/chat-shell";
import type { ChatMessage, ChatRecentRun } from "@/components/chat-shell/types";

vi.mock("@/actions/projects", () => ({
  updateWorkspaceScopeAction: async () => ({}),
}));

vi.mock("@/actions/runs", () => ({
  createAnalysisRunFromChat: async () => ({}),
}));

describe("ChatShell", () => {
  beforeEach(() => {
    HTMLFormElement.prototype.requestSubmit = vi.fn();
  });

  it("renders hydrated history and appends new prompts to the same visible thread", () => {
    const initialMessages: ChatMessage[] = [
      {
        id: "user-run-1",
        role: "user",
        content: "Assess whether margin pressure is temporary or structural for MSFT",
        createdAt: "2026-04-18T19:58:00Z",
      },
      {
        id: "assist-run-1",
        role: "assistant",
        content: "MSFT margin pressure looks cyclical rather than structural.",
        answerCard: {
          goalDisplay: "Assess whether margin pressure is temporary or structural for MSFT",
          summaryLine: "MSFT margin pressure looks cyclical rather than structural.",
          orchestrationStatus: "success",
          conclusionRider: null,
        },
        runId: "run-1",
        runHref: "/projects/project-1/runs/run-1",
        runStatus: "success",
        runCreatedAt: "2026-04-18T19:58:00Z",
        runFinishedAt: "2026-04-18T20:00:00Z",
        createdAt: "2026-04-18T20:00:00Z",
      },
    ];
    const recentRuns: ChatRecentRun[] = [
      {
        id: "run-1",
        href: "/projects/project-1/runs/run-1",
        status: "success",
        goalDisplay: "Assess whether margin pressure is temporary or structural for MSFT",
        createdAt: "2026-04-18T19:58:00Z",
      },
    ];

    render(
      <ChatShell
        projectId="project-1"
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
          background_available: false,
          detail: "Workspace chat is executing synchronously right now.",
        }}
        initialMessages={initialMessages}
        recentRuns={recentRuns}
      />,
    );

    expect(
      screen.getAllByText("Assess whether margin pressure is temporary or structural for MSFT").length,
    ).toBeGreaterThan(1);
    expect(screen.getByText("MSFT margin pressure looks cyclical rather than structural.")).toBeTruthy();

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, {
      target: { value: "Detect unusual financial changes for MSFT" },
    });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

    expect(screen.getAllByText("Detect unusual financial changes for MSFT").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Running analysis...")).toHaveLength(1);
    expect(screen.getAllByText("Workspace chat is executing synchronously right now.").length).toBeGreaterThan(1);
    expect(screen.getAllByText("Assistant").length).toBe(2);
  });
});
