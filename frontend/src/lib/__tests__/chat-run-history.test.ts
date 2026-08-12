/**
 * Thread-list continuity — the sidebar's model of "my other conversations".
 *
 * `buildConversationHistory` had no coverage at all, and it is the module milestone v1.5
 * ("New chat hides the previous conversation") is about. These assert the continuity
 * properties directly, so a regression shows up here rather than in live testing.
 *
 * The ordering case is the subtle one. The backend lists conversations
 * `last_message_at DESC NULLS LAST`, so a brand-new thread — which has no messages — sorts
 * *last* server-side. The sidebar is correct only because it re-sorts on
 * `last_message_at ?? updated_at`. Those two rules have to stay in agreement, and nothing
 * else checks that they do.
 */

import { beforeEach, describe, expect, it, vi } from "vitest";

const { getConversationMock, listConversationsMock, getRunMock, listRunArtifactsMock } =
  vi.hoisted(() => ({
    getConversationMock: vi.fn(),
    listConversationsMock: vi.fn(),
    getRunMock: vi.fn(),
    listRunArtifactsMock: vi.fn(),
  }));

vi.mock("@/lib/api/conversations", () => ({
  getConversation: getConversationMock,
  listConversations: listConversationsMock,
}));

vi.mock("@/lib/api/runs", () => ({
  getRun: getRunMock,
  listRunArtifacts: listRunArtifactsMock,
  listRuns: vi.fn(),
}));

vi.mock("@/lib/api/projects", () => ({
  listProjects: vi.fn(),
}));

import { buildConversationHistory } from "@/lib/chat-run-history";

const PROJECT = "11111111-1111-1111-1111-111111111111";

function conversation(
  overrides: Partial<{
    id: string;
    title: string | null;
    last_message_at: string | null;
    created_at: string;
    updated_at: string;
  }> = {},
) {
  const created = overrides.created_at ?? "2026-08-01T10:00:00Z";
  return {
    id: overrides.id ?? "c-1",
    project_id: PROJECT,
    owner_user_id: "u-1",
    title: overrides.title === undefined ? "Margin question" : overrides.title,
    last_message_at:
      overrides.last_message_at === undefined ? "2026-08-01T10:05:00Z" : overrides.last_message_at,
    archived_at: null,
    created_at: created,
    updated_at: overrides.updated_at ?? created,
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  getConversationMock.mockResolvedValue({ ...conversation(), messages: [] });
});

describe("thread list continuity", () => {
  it("keeps every prior conversation visible when a new empty one is opened", async () => {
    // The v1.5 report: creating a new chat made the previous conversation disappear.
    const fresh = conversation({
      id: "c-new",
      title: null,
      last_message_at: null,
      created_at: "2026-08-02T09:00:00Z",
      updated_at: "2026-08-02T09:00:00Z",
    });
    const older = conversation({ id: "c-old", title: "Earlier question" });
    listConversationsMock.mockResolvedValue([fresh, older]);
    getConversationMock.mockResolvedValue({ ...fresh, messages: [] });

    const { chatThreads } = await buildConversationHistory(PROJECT, "c-new");

    expect(chatThreads.map((t) => t.id)).toEqual(["c-new", "c-old"]);
    expect(chatThreads.find((t) => t.id === "c-old")?.title).toBe("Earlier question");
  });

  it("sorts a brand-new thread first even though the server sorts it last", async () => {
    // Server order is last_message_at DESC NULLS LAST, so the message-less thread arrives
    // at the end. The sidebar must still show it first — it is what the user just created.
    const older = conversation({ id: "c-old", last_message_at: "2026-08-01T10:05:00Z" });
    const fresh = conversation({
      id: "c-new",
      title: null,
      last_message_at: null,
      created_at: "2026-08-02T09:00:00Z",
      updated_at: "2026-08-02T09:00:00Z",
    });
    listConversationsMock.mockResolvedValue([older, fresh]);

    const { chatThreads } = await buildConversationHistory(PROJECT, "c-new");

    expect(chatThreads[0].id).toBe("c-new");
  });

  it("marks an empty thread as having no messages, and a used one as having them", async () => {
    listConversationsMock.mockResolvedValue([
      conversation({ id: "c-new", last_message_at: null }),
      conversation({ id: "c-old" }),
    ]);

    const { chatThreads } = await buildConversationHistory(PROJECT, "c-new");

    expect(chatThreads.find((t) => t.id === "c-new")?.hasMessages).toBe(false);
    expect(chatThreads.find((t) => t.id === "c-old")?.hasMessages).toBe(true);
  });

  it("titles an untitled thread rather than rendering a blank row", async () => {
    listConversationsMock.mockResolvedValue([conversation({ id: "c-new", title: null })]);

    const { chatThreads } = await buildConversationHistory(PROJECT, "c-new");

    expect(chatThreads[0].title).toBe("New chat");
  });

  it("links every thread to its own durable URL", async () => {
    listConversationsMock.mockResolvedValue([
      conversation({ id: "c-a" }),
      conversation({ id: "c-b" }),
    ]);

    const { chatThreads } = await buildConversationHistory(PROJECT, "c-a");

    expect(chatThreads.map((t) => t.href)).toEqual([
      `/projects/${PROJECT}/chat/c-a`,
      `/projects/${PROJECT}/chat/c-b`,
    ]);
  });

  it("lists the open conversation even when the project has only that one", async () => {
    listConversationsMock.mockResolvedValue([conversation({ id: "c-only" })]);

    const { chatThreads } = await buildConversationHistory(PROJECT, "c-only");

    expect(chatThreads).toHaveLength(1);
    expect(chatThreads[0].id).toBe("c-only");
  });
});

describe("message rehydration", () => {
  it("renders a user turn from stored content", async () => {
    listConversationsMock.mockResolvedValue([conversation({ id: "c-1" })]);
    getConversationMock.mockResolvedValue({
      ...conversation({ id: "c-1" }),
      messages: [
        {
          id: "m-1",
          role: "user",
          content: "why did margin fall?",
          created_at: "2026-08-01T10:00:00Z",
          analysis_run_id: null,
        },
      ],
    });

    const { messages } = await buildConversationHistory(PROJECT, "c-1");

    expect(messages).toHaveLength(1);
    expect(messages[0].role).toBe("user");
    expect(messages[0].content).toBe("why did margin fall?");
  });

  it("falls back to the stored narrative when the linked run is gone", async () => {
    // Retention compacts runs; a conversation must stay readable after its run disappears
    // rather than failing the whole thread render.
    listConversationsMock.mockResolvedValue([conversation({ id: "c-1" })]);
    getConversationMock.mockResolvedValue({
      ...conversation({ id: "c-1" }),
      messages: [
        {
          id: "m-2",
          role: "assistant",
          content: "Margin held steady.",
          created_at: "2026-08-01T10:05:00Z",
          analysis_run_id: "run-gone",
        },
      ],
    });
    getRunMock.mockRejectedValue(new Error("404"));
    listRunArtifactsMock.mockRejectedValue(new Error("404"));

    const { messages } = await buildConversationHistory(PROJECT, "c-1");

    expect(messages).toHaveLength(1);
    expect(messages[0].content).toBe("Margin held steady.");
  });
});
