"use client";

import { useActionState, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Search } from "lucide-react";

import { updateWorkspaceScopeAction } from "@/actions/projects";
import {
  deleteConversationAction,
  startNewConversationAction,
} from "@/actions/conversations";
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar";
import {
  cancelAnalysisRun,
  finalizeAnalysisRun,
  getRunProgress,
  startAnalysisRun,
  type ChatReply,
} from "@/actions/runs";
import type { PipelinePhaseView } from "@/lib/run-pipeline-phases";
import type { CurrentUser } from "@/lib/api/types";
import { cn } from "@/lib/utils";
import { ANALYSIS_EXAMPLES } from "@/lib/analysis-examples";
import { ChatComposer } from "./chat-composer";
import { ChatMessageList } from "./chat-message-list";
import { ChatSidebar } from "./chat-sidebar";
import { CommandPalette, type PaletteCommand } from "./command-palette";
import { HelpHint } from "./help-hint";
import type {
  ChatAssistantMessage,
  ChatBackgroundDelivery,
  ChatMessage,
  ChatSystemMessage,
  ChatThreadSummary,
} from "./types";

function nowIso(): string {
  return new Date().toISOString();
}

type Props = {
  projectId: string;
  conversationId: string;
  user?: CurrentUser | null;
  tickers: string[];
  backgroundDelivery: ChatBackgroundDelivery;
  initialMessages: ChatMessage[];
  chatThreads: ChatThreadSummary[];
  className?: string;
};

/**
 * One visible conversation thread, hydrated from persisted messages and extended in place.
 */
export function ChatShell({
  projectId,
  conversationId,
  user,
  tickers,
  backgroundDelivery,
  initialMessages,
  chatThreads,
  className,
}: Props) {
  const router = useRouter();
  const [scopeTickers, setScopeTickers] = useState<string[]>(tickers);
  const [isEditingScope, setIsEditingScope] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  // Resolved after mount so the shortcut hints never cause a hydration mismatch.
  const [modKey, setModKey] = useState("Ctrl");
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [draft, setDraft] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [sendError, setSendError] = useState<string | undefined>(undefined);
  const composerInputRef = useRef<HTMLTextAreaElement>(null);
  const pollTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const activeRequestId = useRef<string | null>(null);
  const activeRunId = useRef<string | null>(null);
  const cancelledRequests = useRef<Set<string>>(new Set());

  useEffect(() => {
    if (/mac|iphone|ipad/i.test(navigator.platform || navigator.userAgent)) setModKey("⌘");
  }, []);

  const handlePickPrompt = useCallback((goal: string) => {
    setDraft(goal);
    requestAnimationFrame(() => composerInputRef.current?.focus());
  }, []);

  const scopeAction = updateWorkspaceScopeAction.bind(null, projectId);
  const [scopeState, scopeFormAction] = useActionState(scopeAction, { tickers });
  const newConversationAction = startNewConversationAction.bind(null, projectId);
  const boundDeleteConversationAction = deleteConversationAction.bind(null, projectId, conversationId);

  useEffect(() => {
    if (scopeState.tickers) {
      setScopeTickers(scopeState.tickers);
    }
  }, [scopeState.tickers]);

  // Stop any in-flight progress poll if the thread unmounts mid-run.
  useEffect(() => () => {
    if (pollTimer.current) clearInterval(pollTimer.current);
  }, []);

  const applyReply = useCallback((reply: ChatReply) => {
    const next: ChatAssistantMessage = {
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
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.role === "assistant" && m.id === next.id);
      if (idx < 0) return [...prev, next];
      const rows = [...prev];
      rows[idx] = next;
      return rows;
    });
  }, []);

  const setPhaseView = useCallback((requestId: string, view: PipelinePhaseView) => {
    setMessages((prev) =>
      prev.map((m) =>
        m.role === "assistant" && m.id === `assist-${requestId}` && m.pending ? { ...m, phaseView: view } : m,
      ),
    );
  }, []);

  const dropPending = useCallback((requestId: string) => {
    setMessages((prev) =>
      prev.filter((m) => !(m.role === "assistant" && m.id === `assist-${requestId}` && m.pending)),
    );
  }, []);

  // Swap the in-flight pending bubble for a system notice (used by Stop) so the
  // user isn't left with a silently vanished message.
  const notePendingStopped = useCallback((requestId: string, content: string) => {
    setMessages((prev) => {
      const note: ChatSystemMessage = {
        id: `sys-stop-${requestId}`,
        role: "system",
        content,
        createdAt: nowIso(),
      };
      const idx = prev.findIndex(
        (m) => m.role === "assistant" && m.id === `assist-${requestId}` && m.pending,
      );
      if (idx < 0) return [...prev, note];
      const rows = [...prev];
      rows[idx] = note;
      return rows;
    });
  }, []);

  // Stop waiting on the in-flight run: unblock the composer immediately and fire a
  // best-effort backend cancel. The run may still finish server-side (its answer then
  // lands in history); this stops the wait, it does not guarantee a mid-run abort.
  const handleStop = useCallback(() => {
    const requestId = activeRequestId.current;
    if (!requestId) return;
    cancelledRequests.current.add(requestId);
    const runId = activeRunId.current;
    // If a run was already handed to the backend, cancel is best-effort — it may
    // still finish and land in history, so say so rather than dropping silently.
    notePendingStopped(
      requestId,
      runId
        ? "Stopped waiting. This analysis may still finish in the background and appear in your history."
        : "Stopped before the analysis started.",
    );
    if (pollTimer.current) {
      clearInterval(pollTimer.current);
      pollTimer.current = null;
    }
    activeRequestId.current = null;
    activeRunId.current = null;
    setIsRunning(false);
    if (runId) void cancelAnalysisRun(runId);
  }, [notePendingStopped]);

  // Escape stops a running analysis — the standard cancel gesture. Skipped while the
  // palette is open, where Escape belongs to dismissing the palette.
  useEffect(() => {
    if (!isRunning) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !paletteOpen) handleStop();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isRunning, handleStop, paletteOpen]);

  const startNewChat = useCallback(() => {
    if (scopeTickers.length === 0) return;
    void newConversationAction(new FormData());
  }, [newConversationAction, scopeTickers.length]);

  // Accelerators: ⌘K / Ctrl+K opens the palette, ⌘⇧O / Ctrl+Shift+O starts a new chat.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const mod = e.metaKey || e.ctrlKey;
      if (!mod) return;
      if (e.key.toLowerCase() === "k") {
        e.preventDefault();
        setPaletteOpen((v) => !v);
        return;
      }
      if (e.shiftKey && e.key.toLowerCase() === "o") {
        e.preventDefault();
        startNewChat();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [startNewChat]);

  const onSend = async (text: string, requestId: string) => {
    setSendError(undefined);
    setIsRunning(true);
    activeRequestId.current = requestId;
    activeRunId.current = null;
    setMessages((prev) => [
      ...prev,
      { id: `user-${requestId}`, role: "user", content: text, createdAt: nowIso() },
      { id: `assist-${requestId}`, role: "assistant", content: "", pending: true, createdAt: nowIso() },
    ]);

    const stopped = () => cancelledRequests.current.has(requestId);

    try {
      const started = await startAnalysisRun(projectId, conversationId, {
        goal: text,
        tickers: scopeTickers,
        requestId,
        refresh: false,
      });
      if (stopped()) return;
      if (started.error) {
        setSendError(started.error);
        dropPending(requestId);
        return;
      }
      if (started.reply) {
        applyReply(started.reply);
        return;
      }
      const runId = started.runId;
      if (!runId) {
        dropPending(requestId);
        return;
      }
      activeRunId.current = runId;

      // Poll real phase progress while the (blocking) execution runs.
      const poll = async () => {
        const progress = await getRunProgress(runId);
        if (progress && !stopped()) setPhaseView(requestId, progress.view);
      };
      void poll();
      if (pollTimer.current) clearInterval(pollTimer.current);
      pollTimer.current = setInterval(() => void poll(), 1400);

      const final = await finalizeAnalysisRun(projectId, conversationId, {
        runId,
        requestId,
        tickers: scopeTickers,
      });
      if (stopped()) return;
      if (final.error) {
        setSendError(final.error);
        dropPending(requestId);
      } else if (final.reply) {
        applyReply(final.reply);
      }
    } finally {
      if (pollTimer.current) {
        clearInterval(pollTimer.current);
        pollTimer.current = null;
      }
      cancelledRequests.current.delete(requestId);
      if (activeRequestId.current === requestId) {
        activeRequestId.current = null;
        activeRunId.current = null;
        setIsRunning(false);
      }
    }
  };

  const paletteCommands: PaletteCommand[] = useMemo(() => {
    const actions: PaletteCommand[] = [
      {
        id: "action-new-chat",
        label: "New chat",
        hint: `${modKey}⇧O`,
        group: "Actions",
        disabled: scopeTickers.length === 0,
        run: startNewChat,
      },
      {
        id: "action-edit-scope",
        label: isEditingScope ? "Close scope editor" : "Edit scope",
        group: "Actions",
        run: () => setIsEditingScope((v) => !v),
      },
    ];
    const prompts: PaletteCommand[] = ANALYSIS_EXAMPLES.map((example, i) => ({
      id: `prompt-${i}`,
      label: example.label,
      hint: example.tickers,
      group: "Starter prompts",
      run: () => handlePickPrompt(example.goal),
    }));
    const threads: PaletteCommand[] = chatThreads.map((thread) => ({
      id: `thread-${thread.id}`,
      label: thread.title,
      hint: thread.id === conversationId ? "current" : undefined,
      group: "Chats",
      run: () => router.push(thread.href),
    }));
    return [...actions, ...threads, ...prompts];
  }, [
    modKey,
    scopeTickers.length,
    startNewChat,
    isEditingScope,
    chatThreads,
    conversationId,
    router,
    handlePickPrompt,
  ]);

  return (
    <SidebarProvider
      className={cn(
        "chat-surface h-full min-h-0 w-full flex-col overflow-hidden bg-[var(--background)] text-[var(--foreground)] md:flex-row",
        className,
      )}
    >
      <CommandPalette open={paletteOpen} onOpenChange={setPaletteOpen} commands={paletteCommands} />
      <ChatSidebar
        conversationId={conversationId}
        user={user}
        scopeTickers={scopeTickers}
        newConversationAction={newConversationAction}
        deleteConversationAction={boundDeleteConversationAction}
        chatThreads={chatThreads}
      />
      <SidebarInset className="bg-[var(--background)]">
        <header className="border-b border-[var(--border)] px-4 py-2.5">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 flex-wrap items-center gap-1.5">
              <span className="text-[10.5px] font-medium uppercase tracking-[0.1em] text-[var(--muted)]">
                Scope
              </span>
              <HelpHint label="What is scope?" title="Analysis scope">
                The companies this chat analyzes, by ticker. Every prompt runs against these
                filings; use <span className="font-medium text-[var(--foreground)]">Edit scope</span> to
                change them.
              </HelpHint>
              {scopeTickers.length > 0 ? (
                scopeTickers.map((ticker) => (
                  <span
                    key={ticker}
                    className="rounded-chip border border-[var(--border)] px-1.5 py-0.5 font-mono text-[11px] text-[var(--foreground)]"
                  >
                    {ticker}
                  </span>
                ))
              ) : (
                <span className="text-[11px] text-[var(--muted)]">none set</span>
              )}
            </div>
            <div className="flex shrink-0 items-center gap-2">
              <button
                type="button"
                onClick={() => setPaletteOpen(true)}
                aria-label={`Open command palette (${modKey}K)`}
                className="flex items-center gap-2 rounded-control border border-[var(--border)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                <Search className="h-3.5 w-3.5" aria-hidden="true" />
                <span className="font-mono">{modKey}K</span>
              </button>
              <button
                type="button"
                onClick={() => setIsEditingScope((v) => !v)}
                className="rounded-control border border-[var(--border)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
              >
                {isEditingScope ? "Close scope" : "Edit scope"}
              </button>
            </div>
          </div>
          {isEditingScope ? (
            <form action={scopeFormAction} className="mt-2 space-y-2 rounded-control border border-[var(--border)] p-2.5">
              <textarea
                name="tickers"
                defaultValue={scopeTickers.join(", ")}
                rows={2}
                className="w-full resize-y rounded-control border border-[var(--border)] bg-[var(--chat-raise)] px-2.5 py-2 font-mono text-[13px]"
              />
              <div className="flex items-center justify-between gap-2">
                <p className="text-[11px] text-[var(--muted)]">
                  Comma or newline separated. This affects future prompts in this chat.
                </p>
                <button
                  type="submit"
                  className="rounded-control border border-[var(--border)] bg-[var(--chat-raise)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--foreground)] transition-colors hover:border-[var(--accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  Save scope
                </button>
              </div>
              {scopeState.error ? (
                <p className="font-mono text-[11px] text-[color:var(--status-danger-ink)]">{scopeState.error}</p>
              ) : null}
            </form>
          ) : null}
        </header>
        <ChatMessageList messages={messages} onPickPrompt={handlePickPrompt} onStop={handleStop} />
        <ChatComposer
          backgroundDelivery={backgroundDelivery}
          error={sendError}
          disabled={isRunning}
          onSend={onSend}
          value={draft}
          onValueChange={setDraft}
          inputRef={composerInputRef}
        />
      </SidebarInset>
    </SidebarProvider>
  );
}
