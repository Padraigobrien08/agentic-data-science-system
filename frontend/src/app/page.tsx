import Link from "next/link";

import { LandingPageClient } from "@/components/landing/landing-page-client";
import { staticShowcase } from "@/lib/api/demos";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveLandingProjectId } from "@/lib/landing-project";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const user = await getCurrentUser();
  const projectId = await resolveLandingProjectId(user);

  return (
    <div className="space-y-12 pb-12">
      <div className="-mx-3 sm:-mx-5 lg:-mx-6">
        <LandingPageClient
          isAuthenticated={!!user}
          projectId={projectId}
          staticShowcase={staticShowcase()}
        />
      </div>
      {user ? (
        <footer className="glass-panel mx-auto max-w-4xl rounded-full border border-white/70 px-5 py-3 text-center text-[11px] text-[var(--muted)]">
          <span>Signed in as {user.email}</span>
          {" · "}
          <Link href="/projects" className="font-medium text-[var(--foreground)] underline decoration-[var(--accent)] underline-offset-4">
            Projects
          </Link>
          {projectId ? (
            <>
              {" · "}
              <Link
                href={`/projects/${projectId}/chat`}
                className="font-medium text-[var(--foreground)] underline decoration-[var(--accent)] underline-offset-4"
              >
                Open chat
              </Link>
            </>
          ) : null}
        </footer>
      ) : null}
    </div>
  );
}
