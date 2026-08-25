import "server-only";

import { staticShowcase } from "@/lib/api/demos";
import { getCurrentUser } from "@/lib/auth/session";
import { resolveLandingProjectId } from "@/lib/landing-project";

/**
 * Whether a reader of a recorded run can actually start one of their own.
 *
 * Derived from the deployment, never declared. The published showcase is a static export
 * with no backend behind it, so its composer is locked — but the same code, cloned and
 * pointed at a backend with its own keys, finds the composer live without a flag to set.
 * That is the point: the lock is a true statement about this instance, not a demo prop.
 */
export type DemoRunGate =
  | { kind: "no_backend" }
  | { kind: "signed_out" }
  | { kind: "no_workspace" }
  | { kind: "ready" };

export async function resolveDemoRunGate(): Promise<DemoRunGate> {
  if (staticShowcase()) {
    return { kind: "no_backend" };
  }
  const user = await getCurrentUser();
  if (!user) {
    return { kind: "signed_out" };
  }
  const projectId = await resolveLandingProjectId(user);
  if (!projectId) {
    return { kind: "no_workspace" };
  }
  return { kind: "ready" };
}
