import "server-only";

import { apiGet } from "@/lib/api/client";
import type { CurrentUser } from "@/lib/api/types";

/** Current user from ``GET /v1/auth/me``, or ``null`` if unauthenticated / invalid token. */
export async function getCurrentUser(): Promise<CurrentUser | null> {
  try {
    return await apiGet<CurrentUser>("/v1/auth/me");
  } catch {
    return null;
  }
}
