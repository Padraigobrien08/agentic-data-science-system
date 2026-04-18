import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { ChatShell } from "@/components/chat-shell/chat-shell";

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

  it("carries workspace delivery posture into the pending assistant message", () => {
    render(
      <ChatShell
        projectId="project-1"
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
          background_available: false,
          detail: "Workspace chat is executing synchronously right now.",
        }}
      />,
    );

    const input = screen.getByLabelText("Message input");
    fireEvent.change(input, {
      target: { value: "Detect unusual financial changes for MSFT" },
    });
    fireEvent.keyDown(input, { key: "Enter", shiftKey: false });

    expect(screen.getAllByText("Detect unusual financial changes for MSFT").length).toBeGreaterThan(1);
    expect(screen.getByText("Running analysis...")).toBeTruthy();
    expect(screen.getAllByText("Workspace chat is executing synchronously right now.").length).toBeGreaterThan(1);
  });
});
