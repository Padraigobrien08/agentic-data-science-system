import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { ChatShell } from "@/components/chat-shell/chat-shell";
import { TraceRail } from "@/components/demos/trace-rail";
import { Pill } from "@/components/investigations/pill";
import { getDemo, getDemoCapture, listDemos } from "@/lib/api/demos";
import { demoMessages, demoThreads } from "@/lib/demo-chat";
import { formatConfidence, outcomeTone } from "@/lib/investigation-view";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>): Promise<Metadata> {
  const { slug } = await params;
  const detail = await getDemo(slug);
  return {
    title: detail?.objective ?? "Recorded investigation",
    description: detail?.conclusion ?? undefined,
  };
}

/**
 * A recorded run, in the product's own chat interface with the trace docked beside it.
 *
 * The same `ChatShell` the live product runs on, in its read-only mode — not a page that
 * resembles it. That is the whole claim of the replay tier: what a visitor sees here is the
 * surface, and the run in it is real. The exhaustive record is one link deeper, at
 * `/demos/[slug]/trace`.
 */
export default async function DemoChatPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const detail = await getDemo(slug);
  if (!detail) {
    notFound();
  }
  // Null in live mode, where model payloads are admin-gated; the page renders without it.
  const capture = await getDemoCapture(slug);
  const demos = await listDemos();
  const fullTraceHref = `/demos/${slug}/trace`;

  const header = (
    <header className="border-b border-[var(--border)] px-4 py-2.5">
      <div className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
        <div className="flex min-w-0 flex-wrap items-center gap-2">
          <span className="rounded-chip border border-[var(--border)] px-1.5 py-0.5 font-mono text-[11px] uppercase tracking-[0.08em] text-[var(--muted)]">
            recorded
          </span>
          <Pill tone={outcomeTone(detail.outcome.kind)} />
          <span className="font-mono text-[11px] text-[var(--chat-faint)]">
            confidence {formatConfidence(detail.confidence)}
          </span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Link
            href="/demos"
            className="rounded-control border border-[var(--border)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            All runs
          </Link>
          {/* Also the only route to the trace below `lg`, where the rail is dropped. */}
          <Link
            href={fullTraceHref}
            className="rounded-control border border-[var(--border)] px-2.5 py-1.5 text-[11px] font-medium text-[var(--muted)] transition-colors hover:text-[var(--foreground)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--accent)]"
          >
            Full record
          </Link>
        </div>
      </div>
    </header>
  );

  return (
    <div className="fixed inset-0 overflow-hidden">
      <ChatShell
        // Same reason as the live conversation page: navigating slug to slug keeps this
        // component at one position in the tree, so without a key React reconciles and the
        // previous run's messages stay on screen.
        key={slug}
        readOnly
        conversationId={slug}
        initialMessages={demoMessages(detail, capture)}
        chatThreads={demoThreads(demos)}
        header={header}
        rail={<TraceRail detail={detail} fullTraceHref={fullTraceHref} />}
        className="h-full min-h-0"
      />
    </div>
  );
}
