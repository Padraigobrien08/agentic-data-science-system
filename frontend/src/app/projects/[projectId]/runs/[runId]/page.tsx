import { redirect } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function RunDetailPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string; runId: string }>;
}>) {
  const { projectId, runId } = await params;
  redirect(`/projects/${projectId}/runs/${runId}/trace`);
}
