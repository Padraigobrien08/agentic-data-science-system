"use client";

import { useActionState, useEffect, useMemo, useState } from "react";

import { ChatComposer } from "./chat-composer";
import { ChatMessageList } from "./chat-message-list";
import { ChatSidebar } from "./chat-sidebar";
import type {
  ChatAssistantMessage,
  ChatBackgroundDelivery,
  ChatMessage,
  ChatSessionStub,
  ChatSystemMessage,
} from "./types";
import { updateWorkspaceScopeAction } from "@/actions/projects";
import { createAnalysisRunFromChat } from "@/actions/runs";

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `m-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

function initialMessages(): ChatMessage[] {
  const boot: ChatSystemMessage = {
    id: "local-1-system",
    role: "system",
    content: "Describe a goal below — each message creates an analysis run for this workspace.",
    createdAt: "local",
  };
  const slot: ChatAssistantMessage = {
    id: "local-1-assistant",
    role: "assistant",
    content: "I’ll return concise analysis updates here with links to run answer and deep dive.",
    createdAt: "local",
  };
  return [boot, slot];
}

type Props = {
  projectId: string;
  tickers: string[];
  backgroundDelivery: ChatBackgroundDelivery;
};

/**
 * Chatbot UI–style workspace: sidebar + message column + composer.
 * Assistant turns are structured frames only (no default prose rendering).
 */
export function ChatShell({ projectId, tickers, backgroundDelivery }: Props) {
  const [scopeTickers, setScopeTickers] = useState<string[]>(tickers);
  const [isEditingScope, setIsEditingScope] = useState(false);
  const [sessions, setSessions] = useState<ChatSessionStub[]>(() => [
    {
      id: "local-1",
      title: "New analysis",
      updatedAt: "local",
    },
  ]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>("local-1");

  const [messagesBySession, setMessagesBySession] = useState<Record<string, ChatMessage[]>>(() => ({
    "local-1": initialMessages(),
  }));

  const messages = useMemo(() => {
    if (!activeSessionId) return [];
    return messagesBySession[activeSessionId] ?? [];
  }, [activeSessionId, messagesBySession]);

  const action = createAnalysisRunFromChat.bind(null, projectId);
  const [state, formAction] = useActionState(action, {});
  const scopeAction = updateWorkspaceScopeAction.bind(null, projectId);
  const [scopeState, scopeFormAction] = useActionState(scopeAction, { tickers });
  useEffect(() => {
    if (scopeState.tickers) {
      setScopeTickers(scopeState.tickers);
    }
  }, [scopeState.tickers]);
  useEffect(() => {
    const reply = state.reply;
    if (!reply || !activeSessionId) return;
    setMessagesBySession((prev) => {
      const rows = [...(prev[activeSessionId] ?? [])];
      const idx = rows.findIndex((m) => m.role === "assistant" && m.id === `assist-${reply.requestId}`);
      const nextAssistant: ChatAssistantMessage = {
        id: `assist-${reply.requestId}`,
        role: "assistant",
        content: reply.content,
        runHref: reply.runHref,
        deepDiveHref: reply.deepDiveHref,
        runsHref: reply.runsHref,
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
      return { ...prev, [activeSessionId]: rows };
    });
  }, [state.reply, activeSessionId]);

  const onNewSession = () => {
    const id = newId();
    const stub: ChatSessionStub = {
      id,
      title: "New conversation",
      updatedAt: nowIso().slice(0, 16).replace("T", " "),
    };
    setSessions((prev) => [stub, ...prev]);
    setMessagesBySession((prev) => ({
      ...prev,
      [id]: initialMessages(),
    }));
    setActiveSessionId(id);
  };

  const onSelectSession = (id: string) => {
    setActiveSessionId(id);
  };
  const onSend = (text: string, requestId: string) => {
    if (!activeSessionId) return;
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
    setMessagesBySession((prev) => ({
      ...prev,
      [activeSessionId]: [...(prev[activeSessionId] ?? []), userMsg, assistantPending],
    }));
    setSessions((prev) =>
      prev.map((s) =>
        s.id === activeSessionId
          ? { ...s, title: text.slice(0, 48) || s.title, updatedAt: nowIso().slice(0, 16).replace("T", " ") }
          : s,
      ),
    );
  };

  return (
    <div className="flex h-[min(calc(100vh-9rem),760px)] min-h-[440px] w-full flex-col overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--background)] shadow-sm md:flex-row">
      <ChatSidebar
        projectId={projectId}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewSession={onNewSession}
        onSelectSession={onSelectSession}
      />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">
        <header className="border-b border-[var(--border)] px-4 py-3">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold tracking-tight text-[var(--foreground)]">Analysis workspace</h2>
              <p className="text-[10px] text-[var(--muted)]">
                Scope:{" "}
                <span className="font-mono text-[var(--foreground)]">
                  {scopeTickers.length ? scopeTickers.join(", ") : "—"}
                </span>
              </p>
            </div>
            <button
              type="button"
              onClick={() => setIsEditingScope((v) => !v)}
              className="rounded border border-[var(--border)] px-2 py-1 text-[10px] text-[var(--foreground)]"
            >
              {isEditingScope ? "Close scope editor" : "Edit scope"}
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
                <p className="text-[10px] text-[var(--muted)]">Comma or newline separated</p>
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
      </div>
    </div>
  );
}
