/**
 * EDGAR chat shell types — provider-agnostic (no OpenAI / model-id coupling).
 * Assistant payloads will later switch to structured blocks; for now `content` is plain text.
 */

export type ChatRole = "user" | "assistant" | "system";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  /** Plain text scaffold; replace with structured assistant blocks in a later step. */
  content: string;
  createdAt: string;
};

/** Local sidebar session stub until backend conversation API exists. */
export type ChatSessionStub = {
  id: string;
  title: string;
  updatedAt: string;
};
