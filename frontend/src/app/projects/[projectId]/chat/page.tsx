import { SignInHint } from "@/components/auth/sign-in-hint";
import { ChatShell } from "@/components/chat-shell/chat-shell";
import { ApiError } from "@/lib/api/errors";
import { getProject } from "@/lib/api/projects";

export const dynamic = "force-dynamic";

/**
 * Chat-style primary workspace shell (Chatbot UI–inspired layout).
 * Local-only messages until wired to run creation / streaming APIs.
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

  return (
    <div className="space-y-3">
      <div>
        <h1 className="text-lg font-semibold">Analysis chat</h1>
        <p className="mt-1 max-w-prose text-xs text-[var(--muted)]">
          Conversation layout scaffold — use Runs for executed analysis today.
        </p>
      </div>
      <ChatShell projectId={projectId} />
    </div>
  );
}
