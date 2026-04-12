"use client";

import { useCallback, useMemo, useState } from "react";

import { ChatComposer } from "./chat-composer";
import { ChatMessageList } from "./chat-message-list";
import { ChatSidebar } from "./chat-sidebar";
import type { ChatAssistantMessage, ChatMessage, ChatSessionStub, ChatSystemMessage } from "./types";

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
    id: newId(),
    role: "system",
    content: "Session is local-only until connected to EDGAR runs.",
    createdAt: nowIso(),
  };
  const slot: ChatAssistantMessage = {
    id: newId(),
    role: "assistant",
    createdAt: nowIso(),
  };
  return [boot, slot];
}

type Props = {
  projectId: string;
};

/**
 * Chatbot UI–style workspace: sidebar + message column + composer.
 * Assistant turns are structured frames only (no default prose rendering).
 */
export function ChatShell({ projectId }: Props) {
  const [sessions, setSessions] = useState<ChatSessionStub[]>(() => [
    {
      id: "local-1",
      title: "New analysis",
      updatedAt: nowIso().slice(0, 16).replace("T", " "),
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

  const onSend = useCallback(
    (text: string) => {
      if (!activeSessionId) return;
      const userMsg: ChatMessage = {
        id: newId(),
        role: "user",
        content: text,
        createdAt: nowIso(),
      };
      const assistantSlot: ChatAssistantMessage = {
        id: newId(),
        role: "assistant",
        createdAt: nowIso(),
      };
      setMessagesBySession((prev) => ({
        ...prev,
        [activeSessionId]: [...(prev[activeSessionId] ?? []), userMsg, assistantSlot],
      }));
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId
            ? { ...s, title: text.slice(0, 48) || s.title, updatedAt: nowIso().slice(0, 16).replace("T", " ") }
            : s,
        ),
      );
    },
    [activeSessionId],
  );

  const onNewSession = useCallback(() => {
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
  }, []);

  const onSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

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
          <h2 className="text-sm font-semibold tracking-tight text-[var(--foreground)]">Analysis workspace</h2>
          <p className="text-[10px] text-[var(--muted)]">Project · structured responses</p>
        </header>
        <ChatMessageList messages={messages} />
        <ChatComposer onSend={onSend} />
      </div>
    </div>
  );
}
