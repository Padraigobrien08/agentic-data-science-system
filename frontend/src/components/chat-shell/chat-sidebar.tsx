"use client";

import { useCallback } from "react";
import { History, MessageSquarePlus, MessagesSquare } from "lucide-react";

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
import type { ChatRecentRun } from "./types";

type Props = {
  scopeTickers: string[];
  newConversationAction: (payload: FormData) => void;
  recentRuns: ChatRecentRun[];
};

/**
 * Conversation-first shadcn sidebar with a new-chat affordance and in-chat history only.
 */
export function ChatSidebar({ scopeTickers, newConversationAction, recentRuns }: Props) {
  const { open } = useSidebar();
  const scrollToAnswer = useCallback((targetId?: string) => {
    if (!targetId) return;
    const node = document.getElementById(targetId);
    if (!node) return;
    node.scrollIntoView({ behavior: "smooth", block: "start" });
  }, []);

  return (
    <Sidebar collapsible="icon" className="group relative bg-[hsl(var(--sidebar-background)/0.96)]">
      <SidebarHeader className="space-y-3 p-2.5">
        <div className="flex items-center justify-between gap-2">
          <SidebarTrigger className="h-8 w-8 rounded-xl border border-[hsl(var(--sidebar-border))] bg-white/75 text-[hsl(var(--sidebar-foreground)/0.75)] hover:bg-white" />
          <form action={newConversationAction}>
            <input type="hidden" name="tickers" value={scopeTickers.join(",")} />
            <SidebarMenuButton
              type="submit"
              className="h-8 w-8 items-center justify-center rounded-xl border border-[hsl(var(--sidebar-border))] bg-white/86 p-0 text-[hsl(var(--sidebar-foreground))] shadow-sm hover:bg-white"
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
              {recentRuns.length === 0 ? (
                <SidebarMenuItem>
                  {open ? (
                    <div className="rounded-xl border border-dashed border-[hsl(var(--sidebar-border))] px-3 py-3 text-xs leading-5 text-[hsl(var(--sidebar-foreground)/0.6)]">
                      Earlier answers in this chat will appear here.
                    </div>
                  ) : (
                    <div className="flex justify-center px-1 py-2 text-[hsl(var(--sidebar-foreground)/0.45)]">
                      <MessagesSquare className="h-4 w-4" />
                    </div>
                  )}
                </SidebarMenuItem>
              ) : null}
              {recentRuns.map((run, index) => (
                <SidebarMenuItem key={run.id}>
                  <SidebarMenuButton
                    type="button"
                    onClick={() => scrollToAnswer(run.scrollTargetId)}
                    isActive={index === 0}
                    className="min-h-0 items-center gap-2 rounded-xl px-2.5 py-2 md:group-data-[state=collapsed]:justify-center"
                    title={run.title}
                  >
                    <MessagesSquare className="mt-0.5 h-4 w-4 shrink-0 text-[hsl(var(--sidebar-foreground)/0.62)]" />
                    {open ? (
                      <div className="min-w-0 flex-1">
                        <span className="line-clamp-2 block text-[12.5px] font-medium leading-5 text-[hsl(var(--sidebar-foreground))]">
                          {run.title}
                        </span>
                      </div>
                    ) : null}
                  </SidebarMenuButton>
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
