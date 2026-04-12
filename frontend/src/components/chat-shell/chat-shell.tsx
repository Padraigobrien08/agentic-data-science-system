"use client";

import { useCallback, useMemo, useState } from "react";

import { ChatComposer } from "./chat-composer";
import { ChatMessageList } from "./chat-message-list";
import { ChatSidebar } from "./chat-sidebar";
import type { ChatMessage, ChatSessionStub } from "./types";

function newId(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) {
    return crypto.randomUUID();
  }
  return `m-${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;
}

function nowIso(): string {
  return new Date().toISOString();
}

const NEW_SESSION_INTRO =
  "New conversation — messages stay in this browser until the EDGAR run API is connected.";

type Props = {
  projectId: string;
};

/**
 * Full-height chat workspace: sidebar + messages + composer.
 * Inspired by Chatbot UI layout; no Supabase, models API, or settings drawer.
 */
export function ChatShell({ projectId }: Props) {
  const [sessions, setSessions] = useState<ChatSessionStub[]>(() => [
    {
      id: "local-1",
      title: "Getting started",
      updatedAt: nowIso().slice(0, 16).replace("T", " "),
    },
  ]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>("local-1");
  const [messagesBySession, setMessagesBySession] = useState<Record<string, ChatMessage[]>>(() => ({
    "local-1": [
      {
        id: newId(),
        role: "assistant",
        content:
          "This is the chat shell scaffold. Use Submit run (nav) for the existing pipeline, or type here once wired to create runs from goals.",
        createdAt: nowIso(),
      },
    ],
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
      const ack: ChatMessage = {
        id: newId(),
        role: "assistant",
        content:
          "Received (local only). Next step: POST a run via the existing backend or stream from a new route — assistant UI will become structured output components.",
        createdAt: nowIso(),
      };
      setMessagesBySession((prev) => ({
        ...prev,
        [activeSessionId]: [...(prev[activeSessionId] ?? []), userMsg, ack],
      }));
      setSessions((prev) =>
        prev.map((s) =>
          s.id === activeSessionId ? { ...s, title: text.slice(0, 48) || s.title, updatedAt: nowIso().slice(0, 16).replace("T", " ") } : s,
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
      [id]: [
        {
          id: newId(),
          role: "system",
          content: NEW_SESSION_INTRO,
          createdAt: nowIso(),
        },
      ],
    }));
    setActiveSessionId(id);
  }, []);

  const onSelectSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  return (
    <div className="flex h-[min(calc(100vh-8rem),720px)] min-h-[420px] w-full flex-col overflow-hidden rounded-lg border border-[var(--border)] md:flex-row">
      <ChatSidebar
        projectId={projectId}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onNewSession={onNewSession}
        onSelectSession={onSelectSession}
      />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col bg-[var(--background)]">
        <header className="border-b border-[var(--border)] px-4 py-3">
          <h2 className="text-sm font-semibold text-[var(--foreground)]">Analysis chat</h2>
          <p className="text-[10px] text-[var(--muted)]">Project {projectId}</p>
        </header>
        <ChatMessageList messages={messages} />
        <ChatComposer onSend={onSend} />
      </div>
    </div>
  );
}
