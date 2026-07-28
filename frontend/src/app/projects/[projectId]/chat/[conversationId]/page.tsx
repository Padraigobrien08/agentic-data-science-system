import { redirect } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ChatShell } from "@/components/chat-shell/chat-shell";
import { ApiError } from "@/lib/api/errors";
import { getProject } from "@/lib/api/projects";
import { getBackgroundDeliveryHealth } from "@/lib/api/runs";
import { buildConversationHistory } from "@/lib/chat-run-history";
import type { BackgroundDeliveryHealth } from "@/lib/api/types";

export const dynamic = "force-dynamic";

/** One durable conversation thread — the conversation-first primary product surface. */
export default async function ConversationPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; conversationId: string }>;
}>) {
  const { projectId, conversationId } = await params;

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

  let history;
  try {
    history = await buildConversationHistory(projectId, conversationId);
  } catch (e) {
    // A missing/deleted conversation resolves back through the chat index.
    if (e instanceof ApiError && e.status === 404) {
      redirect(`/projects/${projectId}/chat`);
    }
    throw e;
  }

  return (
    <div className="fixed inset-x-3 bottom-3 top-[calc(4rem+0.75rem)] overflow-hidden md:inset-x-4 md:bottom-4 md:top-[calc(4rem+1rem)]">
      <ChatShell
        projectId={projectId}
        conversationId={conversationId}
        tickers={project.tickers ?? []}
        backgroundDelivery={backgroundDelivery}
        initialMessages={history.messages}
        chatThreads={history.chatThreads}
        className="h-full min-h-0 rounded-2xl"
      />
    </div>
  );
}
