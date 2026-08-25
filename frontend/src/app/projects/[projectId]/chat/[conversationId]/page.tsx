import { redirect } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ChatShell } from "@/components/chat-shell/chat-shell";
import { ApiError } from "@/lib/api/errors";
import { listDemos } from "@/lib/api/demos";
import { getProject } from "@/lib/api/projects";
import { getBackgroundDeliveryHealth } from "@/lib/api/runs";
import { getCurrentUser } from "@/lib/auth/session";
import { buildConversationHistory } from "@/lib/chat-run-history";
import { mergedThreads } from "@/lib/demo-chat";
import type { BackgroundDeliveryHealth } from "@/lib/api/types";

export const dynamic = "force-dynamic";

/** One durable conversation thread — the conversation-first primary product surface. */
export default async function ConversationPage({
  params,
  searchParams,
}: Readonly<{
  params: Promise<{ projectId: string; conversationId: string }>;
  searchParams?: Promise<{ goal?: string }>;
}>) {
  const { projectId, conversationId } = await params;
  // Carried in from a recorded run: the question is loaded but not sent, so the reader sees
  // it beside their own scope before anything runs against it.
  const goal = (await searchParams)?.goal;

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

  const user = await getCurrentUser();

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

  // Published runs sit in the same history list as the reader's own chats. A failure here
  // costs the showcase rows, not the conversation — the chat must still open without them.
  const demos = await listDemos().catch(() => []);

  return (
    <div className="fixed inset-0 overflow-hidden">
      <ChatShell
        // Remount on thread change. Navigating between conversations keeps this component at
        // the same position in the tree, so React reconciles rather than remounts — and every
        // piece of shell state is seeded from props with `useState`, which only reads them on
        // first mount. Without the key, opening an older chat left the previous thread's
        // messages on screen, a half-typed draft in the composer, and its run-progress poll
        // still running. All of that state is thread-scoped, so discarding it is the point.
        key={conversationId}
        projectId={projectId}
        conversationId={conversationId}
        user={user}
        tickers={project.tickers ?? []}
        backgroundDelivery={backgroundDelivery}
        initialMessages={history.messages}
        chatThreads={mergedThreads(history.chatThreads, demos)}
        initialDraft={goal}
        className="h-full min-h-0"
      />
    </div>
  );
}
