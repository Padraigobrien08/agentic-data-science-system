import Link from "next/link";

import { getCurrentUser } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const defaultProject = process.env.NEXT_PUBLIC_DEFAULT_PROJECT_ID?.trim();
  const user = await getCurrentUser();

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-semibold">EDGAR analysis</h1>
      <p className="max-w-prose text-sm text-[var(--muted)]">
        This UI calls the FastAPI backend from the Next server using{" "}
        <code className="text-xs">API_URL</code> and an HttpOnly session cookie after you{" "}
        <Link href="/login" className="underline">
          sign in
        </Link>
        . Projects, runs, and artifacts require authentication.
      </p>
      <ul className="list-inside list-disc text-sm">
        <li>
          <Link href="/login" className="underline">
            Sign in
          </Link>
        </li>
        <li>
          <Link href="/projects" className="underline">
            Projects (redirects to login if needed)
          </Link>
        </li>
        {user && defaultProject ? (
          <li>
            <Link href={`/projects/${defaultProject}/runs`} className="underline">
              Default project runs
            </Link>
            <span className="ml-1 text-xs text-[var(--muted)]">(env shortcut)</span>
          </li>
        ) : null}
      </ul>
    </div>
  );
}
