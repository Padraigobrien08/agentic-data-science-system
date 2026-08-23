"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";

import { createConversation } from "@/lib/api/conversations";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveRunnableProjectId } from "@/lib/landing-project";

/**
 * Ask your own question, from a recorded run.
 *
 * It opens a fresh conversation in the reader's own workspace rather than extending the
 * recording. A published run is immutable — that is what makes it evidence — and it was run
 * over its own dataset, which is not the reader's scope. Appending to it would produce a
 * thread whose two halves answered different questions about different data.
 *
 * The goal arrives prefilled rather than already running, so the first thing the reader sees
 * is their own scope next to their own question, before anything is spent against it.
 */
export async function startAnalysisFromDemoAction(goal: string) {
  const trimmed = goal.trim();
  if (!trimmed) return;

  // Re-resolved here rather than carried from the page: this runs with the caller's
  // credentials, and a project id crossing the client is a claim, not a fact.
  const user = await getCurrentUser();
  if (!user) {
    redirect("/login?next=/demos");
  }
  // Prefers a workspace with a scope: landing in one without tickers means the composer
  // refuses the very question that was just carried over.
  const projectId = await resolveRunnableProjectId(user);
  if (!projectId) {
    redirect("/projects");
  }

  const conversation = await createConversation(projectId);
  revalidatePath(`/projects/${projectId}/chat`);
  redirect(
    `/projects/${projectId}/chat/${conversation.id}?goal=${encodeURIComponent(trimmed)}`,
  );
}
