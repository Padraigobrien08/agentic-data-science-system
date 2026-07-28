"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createConversation, deleteConversation, listConversations } from "@/lib/api/conversations";

/**
 * Create a new, empty conversation in the current project and open it.
 * Prior conversations remain listed in the sidebar — creating a new chat no longer
 * hides the previous thread.
 */
export async function startNewConversationAction(projectId: string, _formData: FormData) {
  const conversation = await createConversation(projectId);
  revalidatePath(`/projects/${projectId}/chat`);
  redirect(`/projects/${projectId}/chat/${conversation.id}`);
}

/**
 * Delete a conversation and land on the next-most-recent thread (or a fresh one).
 */
export async function deleteConversationAction(
  projectId: string,
  currentConversationId: string,
  formData: FormData,
) {
  const targetId = String(formData.get("conversationId") ?? "").trim();
  if (!targetId) {
    return redirect(`/projects/${projectId}/chat/${currentConversationId}`);
  }

  try {
    await deleteConversation(targetId);
  } catch {
    // Fall through to a safe destination even if the delete failed.
  }

  revalidatePath(`/projects/${projectId}/chat`);

  // Deleting a thread other than the open one keeps the user where they are.
  if (targetId !== currentConversationId) {
    return redirect(`/projects/${projectId}/chat/${currentConversationId}`);
  }

  const remaining = (await listConversations(projectId)).filter((c) => c.id !== targetId);
  if (remaining.length > 0) {
    return redirect(`/projects/${projectId}/chat/${remaining[0].id}`);
  }
  // No threads left — the chat index will mint a fresh one.
  return redirect(`/projects/${projectId}/chat`);
}
