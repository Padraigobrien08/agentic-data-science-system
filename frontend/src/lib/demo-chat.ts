/**
 * A recorded run, expressed in the chat shell's own message types.
 *
 * The demo surface renders the real `ChatShell` rather than a lookalike, so the adapter has
 * to be here: everything the shell shows must come out of persisted state, and anything the
 * run did not record has to stay absent rather than be filled in plausibly.
 */

import type { ChatMessage, ChatThreadSummary } from "@/components/chat-shell/types";
import type { InvestigationDetail, InvestigationSummary } from "@/lib/api/types";
import { composeAnswer } from "@/lib/demo-answer";
import type { DemoCapture } from "@/lib/demo-static/capture-types";

/** The question a run was actually asked, or null when no turn was recorded. */
export function recordedQuestion(capture: DemoCapture | null): string | null {
  for (const thread of capture?.chat ?? []) {
    for (const message of thread.messages) {
      if (message.role === "user" && message.content?.trim()) {
        return message.content;
      }
    }
  }
  return null;
}

/**
 * The conversation for one recorded run: the question, then the answer.
 *
 * Two published runs predate `record_demo.py --chat` and have no user turn. Their objective
 * is *not* promoted into a user bubble — that would put words in a mouth that never spoke —
 * so they open on a system strip that says what the run was given and that nobody typed it.
 */
export function demoMessages(
  detail: InvestigationDetail,
  capture: DemoCapture | null,
): ChatMessage[] {
  const asked = recordedQuestion(capture);
  const answer = composeAnswer(detail);
  const messages: ChatMessage[] = [];

  if (asked) {
    messages.push({
      id: `demo-user-${detail.id}`,
      role: "user",
      content: asked,
      createdAt: detail.created_at,
    });
  } else {
    messages.push({
      id: `demo-goal-${detail.id}`,
      role: "system",
      content: `Recorded before chat turns were captured. The goal this run was given: ${
        detail.objective ?? "not recorded"
      }`,
      createdAt: detail.created_at,
    });
  }

  messages.push({
    id: `demo-assistant-${detail.id}`,
    role: "assistant",
    // The composed view is what renders; `content` is the same claim in one line, so a
    // consumer that only reads text still gets the outcome rather than an empty string.
    content: answer.headline,
    recordedAnswer: answer,
    createdAt: detail.updated_at,
  });

  return messages;
}

/**
 * The published set as the chat sidebar's thread list.
 *
 * The demo index and the run switcher are the same list, so the sidebar *is* the navigation
 * rather than a decoration beside it.
 */
export function demoThreads(demos: InvestigationSummary[]): ChatThreadSummary[] {
  return demos
    .filter((d): d is InvestigationSummary & { demo_slug: string } => !!d.demo_slug)
    .map((d) => ({
      id: d.demo_slug,
      title: d.objective ?? "Recorded investigation",
      href: `/demos/${d.demo_slug}`,
      hasMessages: true,
      updatedAt: d.updated_at,
      recorded: true,
    }));
}

/**
 * The reader's own conversations and the published runs, in one list, newest first.
 *
 * Merged rather than sectioned because they answer the same question — what has been asked
 * here before — and a recorded run is the most useful thing in an empty account's sidebar.
 * The `recorded` flag is what keeps them honest: badged in the list, and not deletable.
 */
export function mergedThreads(
  own: ChatThreadSummary[],
  demos: InvestigationSummary[],
): ChatThreadSummary[] {
  return [...own, ...demoThreads(demos)].sort(
    (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime(),
  );
}
