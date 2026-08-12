/**
 * The conversation page must give ChatShell a fresh instance per thread.
 *
 * Navigating between conversations keeps ChatShell at the same position in the tree, so React
 * reconciles instead of remounting. Every piece of shell state is seeded from props with
 * `useState`, which only reads them on first mount — so without a `key` the previous thread's
 * messages stay on screen, the composer keeps a half-typed draft, and the old run-progress
 * poll keeps running.
 *
 * `key` is not a prop, so it cannot be asserted directly. Its effect can: a keyed child
 * remounts when the key changes. This counts mounts.
 */

import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const { mountSpy, getProjectMock, healthMock, currentUserMock, historyMock } = vi.hoisted(() => ({
  mountSpy: vi.fn(),
  getProjectMock: vi.fn(),
  healthMock: vi.fn(),
  currentUserMock: vi.fn(),
  historyMock: vi.fn(),
}));

vi.mock("@/components/chat-shell/chat-shell", () => {
  const React = require("react");
  return {
    ChatShell: ({ conversationId }: { conversationId: string }) => {
      // Empty deps on purpose: this must fire on *mount only*. With [conversationId] it
      // would also fire when a surviving instance is handed new props, which is exactly the
      // broken case, and the test would pass either way.
      React.useEffect(() => {
        mountSpy(conversationId);
        // eslint-disable-next-line react-hooks/exhaustive-deps
      }, []);
      return React.createElement("div", { "data-testid": "shell" }, conversationId);
    },
  };
});

vi.mock("@/lib/api/projects", () => ({ getProject: getProjectMock }));
vi.mock("@/lib/api/runs", () => ({ getBackgroundDeliveryHealth: healthMock }));
vi.mock("@/lib/auth/session", () => ({ getCurrentUser: currentUserMock }));
vi.mock("@/lib/chat-run-history", () => ({ buildConversationHistory: historyMock }));
vi.mock("next/navigation", () => ({ redirect: vi.fn() }));

import ConversationPage from "./page";

const PROJECT = "11111111-1111-1111-1111-111111111111";

beforeEach(() => {
  vi.clearAllMocks();
  getProjectMock.mockResolvedValue({ id: PROJECT, tickers: ["MSFT"] });
  healthMock.mockResolvedValue({
    delivery_mode: "sync_only",
    background_available: false,
    detail: "",
  });
  currentUserMock.mockResolvedValue(null);
  historyMock.mockImplementation(async (_p: string, conversationId: string) => ({
    messages: [
      {
        id: `m-${conversationId}`,
        role: "user",
        content: `message for ${conversationId}`,
        createdAt: "2026-08-01T10:00:00Z",
      },
    ],
    chatThreads: [],
  }));
});

async function renderPage(conversationId: string) {
  return render(
    await ConversationPage({ params: Promise.resolve({ projectId: PROJECT, conversationId }) }),
  );
}

describe("conversation page", () => {
  it("mounts a fresh shell for each conversation", async () => {
    const { rerender } = await renderPage("c-a");
    expect(screen.getByTestId("shell").textContent).toBe("c-a");

    rerender(
      await ConversationPage({
        params: Promise.resolve({ projectId: PROJECT, conversationId: "c-b" }),
      }),
    );

    expect(screen.getByTestId("shell").textContent).toBe("c-b");
    // Two distinct mounts, not one instance handed new props — the second thread must not
    // inherit the first thread's messages, draft, or in-flight run poll.
    expect(mountSpy.mock.calls.map(([id]) => id)).toEqual(["c-a", "c-b"]);
  });

  it("loads history for the conversation in the URL", async () => {
    await renderPage("c-target");
    expect(historyMock).toHaveBeenCalledWith(PROJECT, "c-target");
  });
});
