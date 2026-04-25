import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "@/components/chat-shell/chat-composer";

describe("ChatComposer", () => {
  it("hides the redundant sync-only banner and removes queue controls", () => {
    render(
      <ChatComposer
        action={vi.fn()}
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
        background_available: false,
        detail: "This chat is executing synchronously right now.",
      }}
      />,
    );

    expect(screen.queryByText("Sync only")).toBeNull();
    expect(screen.queryByText("This chat is executing synchronously right now.")).toBeNull();
    expect(screen.queryByText("Queue for worker")).toBeNull();
    expect(screen.getByText("Chat runs execute immediately in this conversation.")).toBeTruthy();
  });

  it("clears the input after sending a message", () => {
    const action = vi.fn();
    const onSend = vi.fn();
    const requestSubmit = vi.fn();
    vi.spyOn(HTMLFormElement.prototype, "requestSubmit").mockImplementation(requestSubmit);

    render(
      <ChatComposer
        action={action}
        onSend={onSend}
        tickers={["MSFT"]}
        backgroundDelivery={{
          delivery_mode: "sync_only",
        background_available: false,
        detail: "This chat is executing synchronously right now.",
      }}
      />,
    );

    const textarea = screen.getByLabelText("Message input");
    fireEvent.change(textarea, { target: { value: "Find unusual financial changes" } });
    fireEvent.keyDown(textarea, { key: "Enter", code: "Enter", charCode: 13 });

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("Find unusual financial changes", expect.any(String));
    expect((screen.getByLabelText("Message input") as HTMLTextAreaElement).value).toBe("");
    expect(requestSubmit).toHaveBeenCalledTimes(1);
  });
});
