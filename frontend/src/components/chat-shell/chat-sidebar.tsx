"use client";

import Link from "next/link";
import { History, MessageSquarePlus, MessagesSquare, Trash2 } from "lucide-react";

import {
  Sidebar,
  SidebarContent,
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
import type { ChatThreadSummary } from "./types";

type Props = {
  conversationId: string;
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
  scopeTickers,
  newConversationAction,
  deleteConversationAction,
  chatThreads,
}: Props) {
  const { open } = useSidebar();

  return (
    <Sidebar collapsible="icon" className="group relative bg-[hsl(var(--sidebar-background))]">
      <SidebarHeader className="space-y-3 p-2.5">
        <div className="flex items-center justify-between gap-2">
          <SidebarTrigger className="h-8 w-8 rounded-xl border border-[hsl(var(--sidebar-border))] bg-[var(--chat-raise)] text-[hsl(var(--sidebar-foreground)/0.75)] transition-colors hover:border-[var(--accent)]" />
          <form action={newConversationAction}>
            <input type="hidden" name="tickers" value={scopeTickers.join(",")} />
            <SidebarMenuButton
              type="submit"
              className="h-8 w-8 items-center justify-center rounded-xl border border-[hsl(var(--sidebar-border))] bg-[var(--chat-raise)] p-0 text-[hsl(var(--sidebar-foreground))] transition-colors hover:border-[var(--accent)]"
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
                    <div className="rounded-xl border border-dashed border-[hsl(var(--sidebar-border))] px-3 py-3 text-xs leading-5 text-[hsl(var(--sidebar-foreground)/0.6)]">
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
                      className="min-h-0 flex-1 items-center gap-2 rounded-xl px-2.5 py-2 md:group-data-[state=collapsed]:justify-center"
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
                        onSubmit={(event) => {
                          const ok = window.confirm(`Delete chat "${thread.title}"?`);
                          if (!ok) {
                            event.preventDefault();
                          }
                        }}
                      >
                        <input type="hidden" name="conversationId" value={thread.id} />
                        <button
                          type="submit"
                          className="mt-1 flex h-8 w-8 items-center justify-center rounded-lg border border-transparent text-[hsl(var(--sidebar-foreground)/0.46)] transition hover:border-[hsl(var(--sidebar-border))] hover:bg-[var(--chat-raise)] hover:text-red-600 dark:hover:text-red-400"
                          title={`Delete ${thread.title}`}
                          aria-label={`Delete ${thread.title}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </form>
                    ) : null}
                  </div>
                </SidebarMenuItem>
              ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>
      <SidebarRail />
    </Sidebar>
  );
}
