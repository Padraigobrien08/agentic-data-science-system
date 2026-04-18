import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "@/components/chat-shell/chat-composer";

describe("ChatComposer", () => {
  it("renders sync-only chat status and removes queue controls", () => {
    render(
      <ChatComposer
        action={vi.fn()}
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
          background_available: false,
          detail: "Workspace chat is executing synchronously right now.",
        }}
      />,
    );

    expect(screen.getByText("Sync only")).toBeTruthy();
    expect(screen.getByText("Workspace chat is executing synchronously right now.")).toBeTruthy();
    expect(screen.queryByText("Queue for worker")).toBeNull();
    expect(screen.getByText("Chat runs execute immediately in this phase.")).toBeTruthy();
  });
});
