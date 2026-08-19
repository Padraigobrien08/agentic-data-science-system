import { LandingPage } from "@/components/landing/landing-page";
import { listDemos, staticShowcase } from "@/lib/api/demos";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveLandingProjectId } from "@/lib/landing-project";

export const dynamic = "force-dynamic";

/**
 * How many investigations are published, or 0 when that cannot be determined.
 *
 * In live mode this is an HTTP call, and the landing page has to render with no backend at
 * all (D9) — so a failure degrades the copy to a count-free phrasing rather than 500ing the
 * only page a first-time visitor sees.
 */
async function publishedCount(): Promise<number> {
  try {
    return (await listDemos()).length;
  } catch {
    return 0;
  }
}

export default async function HomePage() {
  const user = await getCurrentUser();
  const projectId = await resolveLandingProjectId(user);
  const demoCount = await publishedCount();

  return (
    <LandingPage
      isAuthenticated={!!user}
      projectId={projectId}
      staticShowcase={staticShowcase()}
      userEmail={user?.email ?? null}
      demoCount={demoCount}
    />
  );
}
