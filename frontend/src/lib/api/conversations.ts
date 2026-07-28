import "server-only";

import { apiDelete, apiGet, apiPatch, apiPost } from "./client";
import type {
  ChatMessageCreateBody,
  ChatMessageRead,
  ConversationCreateBody,
  ConversationDetailRead,
  ConversationRead,
} from "./types";

export async function listConversations(projectId: string): Promise<ConversationRead[]> {
  return apiGet<ConversationRead[]>(`/v1/projects/${projectId}/conversations`);
}

export async function createConversation(
  projectId: string,
  body: ConversationCreateBody = {},
): Promise<ConversationRead> {
  return apiPost<ConversationRead>(`/v1/projects/${projectId}/conversations`, body);
}

export async function getConversation(conversationId: string): Promise<ConversationDetailRead> {
  return apiGet<ConversationDetailRead>(`/v1/conversations/${conversationId}`);
}

export async function updateConversation(
  conversationId: string,
  body: { title?: string | null; archived_at?: string | null },
): Promise<ConversationRead> {
  return apiPatch<ConversationRead>(`/v1/conversations/${conversationId}`, body);
}

export async function deleteConversation(conversationId: string): Promise<void> {
  await apiDelete<void>(`/v1/conversations/${conversationId}`);
}

export async function appendChatMessage(
  conversationId: string,
  body: ChatMessageCreateBody,
): Promise<ChatMessageRead> {
  return apiPost<ChatMessageRead>(`/v1/conversations/${conversationId}/messages`, body);
}
