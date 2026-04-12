/**
 * EDGAR chat shell — provider-agnostic. Assistant turns are **not** plain prose;
 * they are containers for structured output (implemented in a follow-up).
 */

export type ChatUserMessage = {
  id: string;
  role: "user";
  content: string;
  createdAt: string;
};

export type ChatSystemMessage = {
  id: string;
  role: "system";
  content: string;
  createdAt: string;
};

/** Assistant message: no `content` field — render only via structured frame. */
export type ChatAssistantMessage = {
  id: string;
  role: "assistant";
  createdAt: string;
};

export type ChatMessage = ChatUserMessage | ChatSystemMessage | ChatAssistantMessage;

export type ChatSessionStub = {
  id: string;
  title: string;
  updatedAt: string;
};
