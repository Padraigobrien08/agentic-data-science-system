import Link from "next/link";

export default function HomePage() {
  const defaultProject = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">EDGAR analysis</h1>
      <p className="max-w-prose text-sm text-[var(--muted)]">
        This UI talks to the FastAPI backend using server-side requests (
        <code className="text-xs">API_URL</code>). Open a project by id to list
        runs, create requests, and inspect traces.
      </p>
      <ul className="list-inside list-disc text-sm">
        <li>
          <Link href="/projects" className="underline">
            Project routes
          </Link>
        </li>
        {defaultProject ? (
          <li>
            <Link href={`/projects/${defaultProject}/runs`} className="underline">
              Default project runs
            </Link>
          </li>
        ) : null}
      </ul>
    </div>
  );
}
