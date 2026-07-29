import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ChatComposer } from "@/components/chat-shell/chat-composer";

describe("ChatComposer", () => {
  it("hides the redundant sync-only banner and removes queue controls", () => {
    render(
      <ChatComposer
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
    expect(screen.queryByText("Refresh SEC cache")).toBeNull();
    expect(screen.queryByText("Chat runs execute immediately in this conversation.")).toBeNull();
    expect(screen.queryByText("Press Enter to submit · Shift+Enter for newline")).toBeNull();
  });

  it("shows the delivery banner only when degraded, not when ready", () => {
    const { rerender } = render(
      <ChatComposer
        backgroundDelivery={{ delivery_mode: "background_ready", background_available: true, detail: null }}
      />,
    );
    expect(screen.queryByText("Background delivery degraded")).toBeNull();

    rerender(
      <ChatComposer
        backgroundDelivery={{ delivery_mode: "background_degraded", background_available: false, detail: null }}
      />,
    );
    expect(screen.getByText("Background delivery degraded")).not.toBeNull();
  });

  it("calls onSend with the text + a request id and clears the input", () => {
    const onSend = vi.fn();

    render(
      <ChatComposer
        onSend={onSend}
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
  });
});
