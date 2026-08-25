import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { CapturePanel } from "@/components/demos/capture-panel";
import { InvestigationDetailView } from "@/components/investigations/investigation-detail";
import { demoArtifactHref, getDemo, getDemoCapture } from "@/lib/api/demos";

export const dynamic = "force-dynamic";

export async function generateMetadata({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>): Promise<Metadata> {
  const { slug } = await params;
  const detail = await getDemo(slug);
  return {
    title: detail ? `Trace — ${detail.objective ?? "investigation"}` : "Trace",
    description: "Every decision, claim, experiment and model call behind a recorded run.",
  };
}

/**
 * The full record behind a recorded run.
 *
 * Separated from the answer on purpose. The transcript is what the reader came for; this is
 * what lets them check it, and burying the whole thing under the answer made both harder to
 * read. Rendered by `InvestigationDetailView`, the same component the authenticated run page
 * uses, so the replay tier is not a prettier parallel implementation.
 */
export default async function DemoTracePage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const detail = await getDemo(slug);
  if (!detail) {
    notFound();
  }
  const capture = await getDemoCapture(slug);

  return (
    <div className="mx-auto w-full max-w-4xl space-y-6 p-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <Link href={`/demos/${slug}`} className="text-sm text-[var(--muted)] underline">
          ← Back to the answer
        </Link>
        <span className="rounded-full border border-[var(--border)] px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wide text-[var(--muted)]">
          recorded · replay tier
        </span>
      </div>

      <InvestigationDetailView
        projectId={null}
        detail={detail}
        artifactHref={(a) => demoArtifactHref(slug, String(a.id))}
      />
      {capture ? <CapturePanel capture={capture} /> : null}
    </div>
  );
}
