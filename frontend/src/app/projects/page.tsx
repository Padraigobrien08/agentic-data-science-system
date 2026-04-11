import Link from "next/link";

export default function ProjectsIndexPage() {
  return (
    <div className="space-y-3 text-sm">
      <h1 className="text-lg font-semibold">Projects</h1>
      <p className="text-[var(--muted)]">
        The API scopes runs by <code className="text-xs">project_id</code> (UUID). Navigate
        directly:
      </p>
      <pre className="overflow-x-auto rounded border border-[var(--border)] bg-[var(--background)] p-3 text-xs">
        /projects/&lt;project-uuid&gt;/runs
      </pre>
      <p className="text-[var(--muted)]">
        Set <code className="text-xs">NEXT_PUBLIC_DEFAULT_PROJECT_ID</code> in{" "}
        <code className="text-xs">.env.local</code> for a shortcut link on the{" "}
        <Link href="/" className="underline">
          home page
        </Link>
        .
      </p>
    </div>
  );
}
