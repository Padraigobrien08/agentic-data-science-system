import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMessageList } from "@/components/chat-shell/chat-message-list";
import type { ChatMessage } from "@/components/chat-shell/types";

describe("ChatMessageList", () => {
  it("renders a structured answer card for completed assistant replies", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-1",
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
        deliveryMode: "sync_only",
        deliveryDetail: "Background delivery was rerouted to immediate execution for this chat request.",
        reroutedFromBackground: true,
        createdAt: "2026-04-18T20:00:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(
      screen.getByText("Background delivery was rerouted to immediate execution for this chat request."),
    ).toBeTruthy();
    expect(screen.getByText("Conclusion")).toBeTruthy();
    expect(screen.getByText("Goal")).toBeTruthy();
    expect(screen.getByText("MSFT margin pressure looks cyclical rather than structural.")).toBeTruthy();
    expect(screen.getByText("Assess whether margin pressure is temporary or structural for MSFT")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Open run" })).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Run answer" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Deep dive" })).toBeNull();
    expect(screen.queryByRole("link", { name: "All runs" })).toBeNull();
  });

  it("renders the structured pending footprint while analysis is running", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-pending",
        role: "assistant",
        content: "Running analysis...",
        pending: true,
        deliveryMode: "sync_only",
        deliveryDetail: "Workspace chat is executing synchronously right now.",
        createdAt: "2026-04-18T20:00:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText("Running analysis...")).toBeTruthy();
    expect(screen.getByText("Updating…")).toBeTruthy();
  });

  it("renders rewriteSuggestions inline without run links for unsupported routing replies", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-unsupported",
        role: "assistant",
        content: "I couldn't route that request yet.",
        routingReason: "Requested tickers fall outside the current workspace scope.",
        rewriteSuggestions: [
          "Assess whether margin pressure is temporary or structural for MSFT.",
          "Compare AAPL versus MSFT on operating margin over the last eight quarters.",
        ],
        createdAt: "2026-04-18T20:05:00Z",
      },
    ];

    render(<ChatMessageList messages={messages} />);

    expect(screen.getByText("Requested tickers fall outside the current workspace scope.")).toBeTruthy();
    expect(
      screen.getByText("Assess whether margin pressure is temporary or structural for MSFT."),
    ).toBeTruthy();
    expect(
      screen.getByText("Compare AAPL versus MSFT on operating margin over the last eight quarters."),
    ).toBeTruthy();
    expect(screen.queryByRole("link", { name: "Open run" })).toBeNull();
    expect(screen.queryByText("Conclusion")).toBeNull();
    expect(screen.queryByText("Goal")).toBeNull();
  });
});
