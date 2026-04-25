import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { ArtifactDetailPanel } from "@/components/trace/artifact-detail-panel";
import { getArtifact } from "@/lib/api/artifacts";
import { ApiError } from "@/lib/api/errors";
import { getRun } from "@/lib/api/runs";

export const dynamic = "force-dynamic";

export default async function ArtifactDetailPage({
  params,
}: Readonly<{
  params: Promise<{ artifactId: string }>;
}>) {
  const { artifactId } = await params;
  let row;
  try {
    row = await getArtifact(artifactId, true);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Artifact</h1>
          <SignInHint nextPath={`/artifacts/${artifactId}`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return <p className="text-sm text-red-700 dark:text-red-400">{msg}</p>;
  }

  let runHref: string | null = null;
  if (row.analysis_run_id) {
    try {
      const r = await getRun(row.analysis_run_id, false);
      runHref = `/projects/${r.project_id}/runs/${r.id}/trace`;
    } catch {
      runHref = null;
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-lg font-semibold">Artifact</h1>
        {runHref ? (
          <Link href={runHref} className="font-mono text-sm underline">
            ← Parent trace
          </Link>
        ) : null}
      </div>
      <ArtifactDetailPanel row={row} runHref={runHref} />
    </div>
  );
}
