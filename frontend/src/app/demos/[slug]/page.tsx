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
    title: detail?.objective ?? "Recorded investigation",
    description: detail?.conclusion ?? undefined,
  };
}

export default async function DemoDetailPage({
  params,
}: Readonly<{ params: Promise<{ slug: string }> }>) {
  const { slug } = await params;
  const detail = await getDemo(slug);
  if (!detail) {
    notFound();
  }
  // Null in live mode, where these payloads are admin-gated — the page renders without it.
  const capture = await getDemoCapture(slug);

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-4">
      <div className="flex items-center justify-between gap-3">
        <Link href="/demos" className="text-sm text-neutral-500 underline dark:text-neutral-400">
          ← All recorded investigations
        </Link>
        <span className="rounded-full border border-neutral-200 px-2.5 py-0.5 font-mono text-[11px] uppercase tracking-wide text-neutral-500 dark:border-neutral-700 dark:text-neutral-400">
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
