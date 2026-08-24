import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { startAnalysisFromDemoAction } from "@/actions/demos";
import { ChatShell, type ReplayComposer } from "@/components/chat-shell/chat-shell";
import { TraceRail } from "@/components/demos/trace-rail";
import { Pill } from "@/components/investigations/pill";
import { getDemo, getDemoChat, listDemos } from "@/lib/api/demos";
import { demoMessages, demoThreads } from "@/lib/demo-chat";
import { resolveDemoRunGate, type DemoRunGate } from "@/lib/demo-run-gate";
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
 * The composer's state, said plainly.
 *
 * Each locked case names the one thing that is missing and how to remove it, because the
 * lock is the most interesting thing on the page for a reader deciding whether any of this
 * is real: it is the difference between a screenshot and a running system with the power
 * switch off.
 */
function replayComposer(gate: DemoRunGate): ReplayComposer {
  if (gate.kind === "ready") {
    return {
      state: "ready",
      placeholder: "Ask your own question…",
      start: startAnalysisFromDemoAction,
    };
  }
  if (gate.kind === "signed_out") {
    return {
      state: "locked",
      lock: {
        short: "Sign in to ask your own question",
        detail: (
          <>
            This run is a recording, but the backend behind it is live. Sign in and the
            composer starts a new analysis in your own workspace.
          </>
        ),
      },
    };
  }
  if (gate.kind === "no_workspace") {
    return {
      state: "locked",
      lock: {
        short: "Create a workspace to ask your own question",
        detail: (
          <>
            You are signed in, but have no workspace yet. Create one and this composer starts
            a new analysis in it.
          </>
        ),
      },
    };
  }
  return {
    state: "locked",
    lock: {
      short: "Recorded run — this build has no backend attached",
      detail: (
        <>
          The published showcase is a static export: the runs are real, but there is no
          server here to run new ones against.{" "}
          <span className="text-[var(--foreground)]">
            Clone the repo, point it at a database and your own model API key, and this
            composer goes live
          </span>{" "}
          — nothing to switch on, it reads the deployment.
        </>
      ),
    },
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
  // Served on both tiers now: the turns are public, the model payloads behind them are not.
  const chat = await getDemoChat(slug);
  const demos = await listDemos();
  const gate = await resolveDemoRunGate();
  const fullTraceHref = `/demos/${slug}/trace`;

  // Keyed because these are created here and rendered as siblings inside a client
  // component; React cannot infer a static position across that boundary.
  const header = (
    <header key="demo-header" className="border-b border-[var(--border)] px-4 py-2.5">
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
        initialMessages={demoMessages(detail, chat)}
        chatThreads={demoThreads(demos)}
        header={header}
        rail={<TraceRail key="demo-rail" detail={detail} fullTraceHref={fullTraceHref} />}
        defaultRailOpen
        composer={replayComposer(gate)}
        className="h-full min-h-0"
      />
    </div>
  );
}
