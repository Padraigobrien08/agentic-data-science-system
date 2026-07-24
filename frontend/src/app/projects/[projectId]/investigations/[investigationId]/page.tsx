import Link from "next/link";
import { notFound } from "next/navigation";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { InvestigationDetailView } from "@/components/investigations/investigation-detail";
import { getInvestigation } from "@/lib/api/investigations";
import { ApiError } from "@/lib/api/errors";

export const dynamic = "force-dynamic";

export default async function InvestigationDetailPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; investigationId: string }>;
}>) {
  const { projectId, investigationId } = await params;

  let detail;
  try {
    detail = await getInvestigation(investigationId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      notFound();
    }
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Investigation</h1>
          <SignInHint nextPath={`/projects/${projectId}/investigations/${investigationId}`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return <p className="text-sm text-red-700 dark:text-red-400">{msg}</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-4">
      <Link
        href={`/projects/${projectId}/investigations`}
        className="text-sm text-neutral-500 underline dark:text-neutral-400"
      >
        ← All investigations
      </Link>
      <InvestigationDetailView projectId={projectId} detail={detail} />
    </div>
  );
}
