import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { DemoTranscript } from "@/components/demos/demo-transcript";
import { TraceRail } from "@/components/demos/trace-rail";
import { getDemo, getDemoCapture } from "@/lib/api/demos";

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
 * A recorded run, as a conversation with the trace docked beside it.
 *
 * This is the demo's front door because it is what the product actually looks like; the
 * exhaustive record is one link deeper, at `/demos/[slug]/trace`. A reader who wants the
 * answer gets the answer, and a reader who wants to disbelieve it never has to go looking.
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

  return (
    <div className="mx-auto w-full max-w-[80rem] space-y-6 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href="/demos" className="text-sm text-[var(--muted)] underline">
          ← All recorded investigations
        </Link>
        <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wide text-[var(--muted)]">
          recorded · replay tier
        </span>
      </div>

      <div className="grid gap-8 lg:grid-cols-[minmax(0,1fr)_26rem]">
        <DemoTranscript detail={detail} capture={capture} />
        <div className="lg:border-l lg:border-[var(--border)] lg:pl-8">
          <TraceRail detail={detail} fullTraceHref={`/demos/${slug}/trace`} />
        </div>
      </div>
    </div>
  );
}
