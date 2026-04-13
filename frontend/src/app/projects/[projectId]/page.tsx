import { redirect } from "next/navigation";

export default async function ProjectOverviewPage({
  params,
}: Readonly<{
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;
  redirect(`/projects/${projectId}/chat`);
}
