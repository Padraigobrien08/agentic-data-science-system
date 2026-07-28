import { redirect } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { createConversation, listConversations } from "@/lib/api/conversations";
import { ApiError } from "@/lib/api/errors";
import { getProject } from "@/lib/api/projects";

export const dynamic = "force-dynamic";

/**
 * Chat entry point. Resolves the project to a concrete conversation so every chat URL
 * points at a durable thread — opening the newest, or minting a fresh one if none exist.
 */
export default async function ProjectChatPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;

  try {
    await getProject(projectId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Analysis chat</h1>
          <SignInHint nextPath={`/projects/${projectId}/chat`} />
        </div>
      );
    }
    throw e;
  }

  const conversations = await listConversations(projectId);
  const target = conversations[0] ?? (await createConversation(projectId));
  redirect(`/projects/${projectId}/chat/${target.id}`);
}
