"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, History, LogOut, MessageSquarePlus, MessagesSquare, Trash2, X } from "lucide-react";

import { logoutAction } from "@/actions/auth";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarTrigger,
  useSidebar,
} from "@/components/ui/sidebar";
import type { CurrentUser } from "@/lib/api/types";
import type { ChatThreadSummary } from "./types";

type Props = {
  conversationId: string;
  user?: CurrentUser | null;
  scopeTickers: string[];
  newConversationAction: (payload: FormData) => void;
  deleteConversationAction: (payload: FormData) => void;
  chatThreads: ChatThreadSummary[];
};

/**
 * Conversation-first shadcn sidebar with a new-chat affordance and durable chat history.
 */
export function ChatSidebar({
  conversationId,
  user,
  scopeTickers,
  newConversationAction,
  deleteConversationAction,
  chatThreads,
}: Props) {
  const { open } = useSidebar();
  const [confirmingId, setConfirmingId] = useState<string | null>(null);

  const isGuest = !user || user.email.endsWith("@demo.local");
  const accountName = isGuest ? "Guest" : user.display_name || user.email.split("@")[0];
  const accountSub = isGuest ? "Demo session" : user.email;
  const accountInitial = (accountName[0] || "G").toUpperCase();

  return (
    <Sidebar collapsible="icon" className="group relative bg-[hsl(var(--sidebar-background))]">
      <SidebarHeader className="space-y-3 p-2.5">
        <div className="flex items-center justify-between gap-2">
          <SidebarTrigger className="h-8 w-8 rounded-control border border-[hsl(var(--sidebar-border))] bg-[var(--chat-raise)] text-[hsl(var(--sidebar-foreground)/0.75)] transition-colors hover:border-[var(--accent)]" />
          <form action={newConversationAction}>
            <input type="hidden" name="tickers" value={scopeTickers.join(",")} />
            <SidebarMenuButton
              type="submit"
              className="h-8 w-8 items-center justify-center rounded-control border border-[hsl(var(--sidebar-border))] bg-[var(--chat-raise)] p-0 text-[hsl(var(--sidebar-foreground))] transition-colors hover:border-[var(--accent)]"
              disabled={scopeTickers.length === 0}
              title="New chat"
              aria-label="New chat"
            >
              <MessageSquarePlus className="h-4 w-4 shrink-0 text-[hsl(var(--sidebar-foreground)/0.7)]" />
            </SidebarMenuButton>
          </form>
        </div>
      </SidebarHeader>
      <SidebarContent aria-label="Chat history" className="px-1 pb-2">
        <SidebarGroup className="pt-2">
          <SidebarGroupLabel className="flex items-center gap-2 px-3">
            <History className="h-3.5 w-3.5" />
            <span>History</span>
          </SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu className="px-1">
              {chatThreads.length === 0 ? (
                <SidebarMenuItem>
                  {open ? (
                    <div className="rounded-control border border-dashed border-[hsl(var(--sidebar-border))] px-3 py-3 text-xs leading-5 text-[hsl(var(--sidebar-foreground)/0.6)]">
                      Earlier chats will appear here.
                    </div>
                  ) : (
                    <div className="flex justify-center px-1 py-2 text-[hsl(var(--sidebar-foreground)/0.45)]">
                      <MessagesSquare className="h-4 w-4" />
                    </div>
                  )}
                </SidebarMenuItem>
              ) : null}
              {chatThreads.map((thread) => (
                <SidebarMenuItem key={thread.id}>
                  <div className="flex items-start gap-1.5">
                    <SidebarMenuButton
                      asChild
                      isActive={thread.id === conversationId}
                      className="min-h-0 flex-1 items-center gap-2 rounded-control px-2.5 py-2 md:group-data-[state=collapsed]:justify-center"
                      title={thread.title}
                    >
                      <Link href={thread.href}>
                        <MessagesSquare className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--sidebar-foreground)/0.62)]" />
                        {open ? (
                          <div className="min-w-0 flex-1">
                            <span className="line-clamp-2 block text-[13px] font-medium leading-5 text-[hsl(var(--sidebar-foreground))]">
                              {thread.title}
                            </span>
                          </div>
                        ) : null}
                      </Link>
                    </SidebarMenuButton>
                    {open ? (
                      <form
                        action={deleteConversationAction}
                        onSubmit={() => setConfirmingId(null)}
                      >
                        <input type="hidden" name="conversationId" value={thread.id} />
                        {confirmingId === thread.id ? (
                          <div className="mt-1 flex items-center gap-1">
                            <button
                              type="submit"
                              className="flex h-8 w-8 items-center justify-center rounded-control border border-[color:var(--status-danger-border)] bg-[var(--status-danger-bg)] text-[color:var(--status-danger-ink)] transition hover:brightness-110 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                              title={`Confirm delete ${thread.title}`}
                              aria-label={`Confirm delete ${thread.title}`}
                            >
                              <Check className="h-3.5 w-3.5" />
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmingId(null)}
                              className="flex h-8 w-8 items-center justify-center rounded-control border border-[hsl(var(--sidebar-border))] text-[hsl(var(--sidebar-foreground)/0.6)] transition hover:bg-[var(--chat-raise)] hover:text-[hsl(var(--sidebar-foreground))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                              title="Cancel"
                              aria-label={`Cancel deleting ${thread.title}`}
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          </div>
                        ) : (
                          <button
                            type="button"
                            onClick={() => setConfirmingId(thread.id)}
                            className="mt-1 flex h-8 w-8 items-center justify-center rounded-control border border-transparent text-[hsl(var(--sidebar-foreground)/0.46)] transition hover:border-[hsl(var(--sidebar-border))] hover:bg-[var(--chat-raise)] hover:text-[color:var(--status-danger-ink)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                            title={`Delete ${thread.title}`}
                            aria-label={`Delete ${thread.title}`}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        )}
                      </form>
                    ) : null}
                  </div>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter className="p-2">
        <div className="flex items-center gap-2 rounded-control px-1.5 py-1">
          <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--chat-primary)] text-[11px] font-semibold text-[var(--chat-primary-ink)]">
            {accountInitial}
          </span>
          {open ? (
            <>
              <div className="min-w-0 flex-1 leading-tight">
                <p className="truncate text-[13px] font-medium text-[hsl(var(--sidebar-foreground))]">
                  {accountName}
                </p>
                <p className="truncate text-[11px] text-[hsl(var(--sidebar-foreground)/0.6)]">{accountSub}</p>
              </div>
              <form action={logoutAction}>
                <button
                  type="submit"
                  title="Sign out"
                  aria-label="Sign out"
                  className="flex h-8 w-8 items-center justify-center rounded-control text-[hsl(var(--sidebar-foreground)/0.55)] transition hover:bg-[var(--chat-hover)] hover:text-[hsl(var(--sidebar-foreground))] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </form>
            </>
          ) : null}
        </div>
      </SidebarFooter>
      <SidebarRail />
    </Sidebar>
  );
}
