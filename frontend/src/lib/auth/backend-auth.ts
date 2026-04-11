import "server-only";

import { cookies } from "next/headers";

import { SESSION_COOKIE_NAME } from "./constants";

/** Headers to pass through to FastAPI for authenticated routes. */
export async function bearerAuthHeaders(): Promise<Record<string, string>> {
  const jar = await cookies();
  const token = jar.get(SESSION_COOKIE_NAME)?.value;
  return token ? { Authorization: `Bearer ${token}` } : {};
}
