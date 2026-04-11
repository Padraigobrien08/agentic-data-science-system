import { ProjectNav } from "@/components/layout/project-nav";

export default async function ProjectLayout({
  children,
  params,
}: Readonly<{
  children: React.ReactNode;
  params: Promise<{ projectId: string }>;
}>) {
  const { projectId } = await params;

  return (
    <div className="space-y-4">
      <div>
        <p className="text-xs text-[var(--muted)]">Project</p>
        <p className="font-mono text-sm break-all">{projectId}</p>
      </div>
      <ProjectNav projectId={projectId} />
      {children}
    </div>
  );
}
