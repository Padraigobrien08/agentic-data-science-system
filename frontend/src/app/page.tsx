import { LandingPage } from "@/components/landing/landing-page";
import { listDemos, staticShowcase } from "@/lib/api/demos";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveLandingProjectId } from "@/lib/landing-project";

export const dynamic = "force-dynamic";

/**
 * The run "Explore recorded runs" opens.
 *
 * It lands in a conversation rather than on the index, because the point of the link is to
 * show what the product looks like, and the product is a chat. This one is the strongest of
 * the set: it carries a recorded chat turn, and it is the run where the loop caught itself
 * holding two claims that could not both be true.
 *
 * Named rather than derived — "the best demo" is an editorial call, not something to infer —
 * but checked against what is actually published, so unpublishing it degrades to the index
 * instead of a 404.
 */
const FEATURED_DEMO_SLUG = "csv-staffing-vs-service";

/**
 * The published set, or empty when it cannot be determined.
 *
 * In live mode this is an HTTP call, and the landing page has to render with no backend at
 * all (D9) — so a failure degrades the copy and the link rather than 500ing the only page a
 * first-time visitor sees.
 */
async function publishedDemos() {
  try {
    return await listDemos();
  } catch {
    return [];
  }
}

export default async function HomePage() {
  const user = await getCurrentUser();
  const projectId = await resolveLandingProjectId(user);
  const demos = await publishedDemos();
  const featured = demos.some((d) => d.demo_slug === FEATURED_DEMO_SLUG)
    ? `/demos/${FEATURED_DEMO_SLUG}`
    : "/demos";

  return (
    <LandingPage
      isAuthenticated={!!user}
      projectId={projectId}
      staticShowcase={staticShowcase()}
      userEmail={user?.email ?? null}
      demoCount={demos.length}
      demoHref={featured}
    />
  );
}
