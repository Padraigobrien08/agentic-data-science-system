import Link from "next/link";

import { LandingPageClient } from "@/components/landing/landing-page-client";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveLandingProjectId } from "@/lib/landing-project";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const user = await getCurrentUser();
  const projectId = await resolveLandingProjectId(user);

  return (
    <div className="space-y-10 pb-8">
      <LandingPageClient isAuthenticated={!!user} projectId={projectId} />
      {user ? (
        <footer className="mx-auto max-w-2xl border-t border-[var(--border)] pt-6 text-center text-[11px] text-[var(--muted)]">
          <span>Signed in as {user.email}</span>
          {" · "}
          <Link href="/projects" className="underline">
            Projects
          </Link>
          {projectId ? (
            <>
              {" · "}
              <Link href={`/projects/${projectId}/chat`} className="underline">
                Chat workspace
              </Link>
            </>
          ) : null}
        </footer>
      ) : null}
    </div>
  );
}
