"use client";

import { useActionState, useEffect, useState } from "react";

import {
  deleteChatAction,
  startConversationFromScopeAction,
  updateWorkspaceScopeAction,
} from "@/actions/projects";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import { createAnalysisRunFromChat } from "@/actions/runs";
import { cn } from "@/lib/utils";
import { ChatComposer } from "./chat-composer";
import { ChatMessageList } from "./chat-message-list";
import { ChatSidebar } from "./chat-sidebar";
import type { ChatAssistantMessage, ChatBackgroundDelivery, ChatMessage, ChatThreadSummary } from "./types";

function nowIso(): string {
  return new Date().toISOString();
}

type Props = {
  projectId: string;
  tickers: string[];
  backgroundDelivery: ChatBackgroundDelivery;
  initialMessages: ChatMessage[];
  chatThreads: ChatThreadSummary[];
  className?: string;
};

/**
 * One visible conversation thread, hydrated from persisted runs and extended in place.
 */
export function ChatShell({
  projectId,
  tickers,
  backgroundDelivery,
  initialMessages,
  chatThreads,
  className,
}: Props) {
  const [scopeTickers, setScopeTickers] = useState<string[]>(tickers);
  const [isEditingScope, setIsEditingScope] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);

  const action = createAnalysisRunFromChat.bind(null, projectId);
  const [state, formAction] = useActionState(action, {});
  const scopeAction = updateWorkspaceScopeAction.bind(null, projectId);
  const [scopeState, scopeFormAction] = useActionState(scopeAction, { tickers });
  const newConversationAction = startConversationFromScopeAction.bind(null, projectId);
  const deleteConversationAction = deleteChatAction.bind(null, projectId);

  useEffect(() => {
    if (scopeState.tickers) {
      setScopeTickers(scopeState.tickers);
    }
  }, [scopeState.tickers]);

  useEffect(() => {
    const reply = state.reply;
    if (!reply) return;
    setMessages((prev) => {
      const rows = [...prev];
      const idx = rows.findIndex((m) => m.role === "assistant" && m.id === `assist-${reply.requestId}`);
      const nextAssistant: ChatAssistantMessage = {
        id: `assist-${reply.requestId}`,
        role: "assistant",
        content: reply.content,
        rewriteSuggestions: reply.rewriteSuggestions,
        routingReason: reply.routingReason,
        answerCard: reply.answerCard,
        runId: reply.runId,
        runHref: reply.runHref,
        runStatus: reply.runStatus,
        runCreatedAt: reply.runCreatedAt,
        runFinishedAt: reply.runFinishedAt,
        deliveryMode: reply.deliveryMode,
        deliveryDetail: reply.deliveryDetail,
        reroutedFromBackground: reply.reroutedFromBackground,
        createdAt: nowIso(),
      };
      if (idx >= 0) {
        rows[idx] = nextAssistant;
      } else {
        rows.push(nextAssistant);
      }
      return rows;
    });
  }, [state.reply]);

  const onSend = (text: string, requestId: string) => {
    const userMsg: ChatMessage = {
      id: `user-${requestId}`,
      role: "user",
      content: text,
      createdAt: nowIso(),
    };
    const assistantPending: ChatAssistantMessage = {
      id: `assist-${requestId}`,
      role: "assistant",
      content: "Running analysis...",
      pending: true,
      deliveryMode: backgroundDelivery.delivery_mode,
      deliveryDetail: backgroundDelivery.detail ?? undefined,
      reroutedFromBackground: false,
      createdAt: nowIso(),
    };
    setMessages((prev) => [...prev, userMsg, assistantPending]);
  };

  return (
    <SidebarProvider
      className={cn(
        "h-[min(calc(100dvh-9rem),760px)] min-h-[440px] w-full flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--background)] shadow-sm md:flex-row",
        className,
      )}
    >
      <ChatSidebar
        projectId={projectId}
        scopeTickers={scopeTickers}
        newConversationAction={newConversationAction}
        deleteConversationAction={deleteConversationAction}
        chatThreads={chatThreads}
      />
      <SidebarInset className="bg-[var(--background)]">
        <header className="border-b border-[var(--border)] px-4 py-2.5">
          <div className="flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={() => setIsEditingScope((v) => !v)}
              className="rounded border border-[var(--border)] px-2 py-1 text-[10px] text-[var(--foreground)]"
            >
              {isEditingScope ? "Close scope" : "Edit scope"}
            </button>
          </div>
          {isEditingScope ? (
            <form action={scopeFormAction} className="mt-2 space-y-2 rounded border border-[var(--border)] p-2">
              <textarea
                name="tickers"
                defaultValue={scopeTickers.join(", ")}
                rows={2}
                className="w-full resize-y rounded border border-[var(--border)] bg-transparent px-2 py-1.5 font-mono text-xs"
              />
              <div className="flex items-center justify-between gap-2">
                <p className="text-[10px] text-[var(--muted)]">
                  Comma or newline separated. This affects future prompts in this chat.
                </p>
                <button
                  type="submit"
                  className="rounded border border-[var(--border)] px-2 py-1 text-[10px] text-[var(--foreground)]"
                >
                  Save scope
                </button>
              </div>
              {scopeState.error ? (
                <p className="font-mono text-[10px] text-red-700 dark:text-red-400">{scopeState.error}</p>
              ) : null}
            </form>
          ) : null}
        </header>
        <ChatMessageList messages={messages} />
        <ChatComposer
          action={formAction}
          backgroundDelivery={backgroundDelivery}
          error={state.error}
          tickers={scopeTickers}
          onSend={onSend}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}
