import Link from "next/link";

import { SignInHint } from "@/components/auth/sign-in-hint";
import { InvestigationSummaryList } from "@/components/investigations/investigation-summary-list";
import { listInvestigations } from "@/lib/api/investigations";
import { ApiError } from "@/lib/api/errors";

export const dynamic = "force-dynamic";

export default async function InvestigationsListPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;

  let investigations;
  try {
    investigations = await listInvestigations(projectId);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401) {
      return (
        <div className="space-y-3">
          <h1 className="text-lg font-semibold">Investigations</h1>
          <SignInHint nextPath={`/projects/${projectId}/investigations`} />
        </div>
      );
    }
    const msg = e instanceof ApiError ? e.body || e.message : "Unknown error";
    return <p className="text-sm text-red-700 dark:text-red-400">{msg}</p>;
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5 p-4">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h1 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
          Investigations
        </h1>
        <Link
          href={`/projects/${projectId}/chat`}
          className="text-sm text-neutral-500 underline dark:text-neutral-400"
        >
          ← Back to chat
        </Link>
      </div>
      <p className="text-sm text-neutral-500 dark:text-neutral-400">
        Adaptive investigations over your datasets — each with the hypotheses it tested, the
        evidence it gathered, and the decisions it made.
      </p>
      <InvestigationSummaryList projectId={projectId} investigations={investigations} />
    </div>
  );
}
