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

export type ChatAssistantMessage = {
  id: string;
  role: "assistant";
  content: string;
  runHref?: string;
  deepDiveHref?: string;
  runsHref?: string;
  pending?: boolean;
  createdAt: string;
};

export type ChatMessage = ChatUserMessage | ChatSystemMessage | ChatAssistantMessage;

export type ChatSessionStub = {
  id: string;
  title: string;
  updatedAt: string;
};
