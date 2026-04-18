import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ChatMessageList } from "@/components/chat-shell/chat-message-list";
import type { ChatMessage } from "@/components/chat-shell/types";

describe("ChatMessageList", () => {
  it("renders rerouted delivery notes alongside run navigation links", () => {
    const messages: ChatMessage[] = [
      {
        id: "assistant-1",
        role: "assistant",
        content: "Analysis completed for MSFT. Open run answer or deep dive when ready.",
        runHref: "/projects/project-1/runs/run-1",
        deepDiveHref: "/projects/project-1/runs/run-1/trace",
        runsHref: "/projects/project-1/runs",
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
    expect(screen.getByRole("link", { name: "Run answer" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "Deep dive" })).toBeTruthy();
    expect(screen.getByRole("link", { name: "All runs" })).toBeTruthy();
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
    expect(screen.queryByRole("link", { name: "Run answer" })).toBeNull();
    expect(screen.queryByRole("link", { name: "Deep dive" })).toBeNull();
    expect(screen.queryByRole("link", { name: "All runs" })).toBeNull();
  });
});
