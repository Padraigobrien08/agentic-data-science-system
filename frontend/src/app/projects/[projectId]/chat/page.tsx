import { SignInHint } from "@/components/auth/sign-in-hint";
import { ChatShell } from "@/components/chat-shell/chat-shell";
import { ProjectWorkspaceNav } from "@/components/layout/project-workspace-nav";
import { ApiError } from "@/lib/api/errors";
import { getProject } from "@/lib/api/projects";
import { getBackgroundDeliveryHealth } from "@/lib/api/runs";
import { buildProjectChatHistory } from "@/lib/chat-run-history";
import type { BackgroundDeliveryHealth } from "@/lib/api/types";

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

  let project;
  let backgroundDelivery: BackgroundDeliveryHealth = {
    delivery_mode: "background_degraded",
    background_available: false,
    detail: "Background delivery status is currently unavailable.",
  };
  try {
    project = await getProject(projectId);
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
  try {
    backgroundDelivery = await getBackgroundDeliveryHealth();
  } catch {
    // Keep the fallback degraded posture so chat never implies background delivery is healthy.
  }
  const history = await buildProjectChatHistory(projectId);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-lg font-semibold">Workspace chat</h1>
        <p className="mt-1 max-w-prose text-xs text-[var(--muted)]">
          Ask questions against this workspace’s ticker scope. Completed analyses appear inline here first, with the
          standalone run page reserved for secondary inspection when you need to dig deeper.
        </p>
      </div>
      <ProjectWorkspaceNav projectId={projectId} current="chat" />
      <ChatShell
        projectId={projectId}
        tickers={project.tickers ?? []}
        backgroundDelivery={backgroundDelivery}
        initialMessages={history.messages}
        recentRuns={history.recentRuns}
      />
    </div>
  );
}
