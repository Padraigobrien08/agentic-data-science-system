import { LandingPage } from "@/components/landing/landing-page";
import { staticShowcase } from "@/lib/api/demos";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveLandingProjectId } from "@/lib/landing-project";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  const user = await getCurrentUser();
  const projectId = await resolveLandingProjectId(user);

  return (
    <LandingPage
      isAuthenticated={!!user}
      projectId={projectId}
      staticShowcase={staticShowcase()}
      userEmail={user?.email ?? null}
    />
  );
}
