/**
 * Backend origin for server-side fetches (RSC, route handlers, server actions).
 * Not exposed to the browser — avoids depending on FastAPI CORS for mutations.
 */
export function getApiBaseUrl(): string {
  const url = process.env.API_URL?.trim();
  if (!url) {
    throw new Error(
      "Missing API_URL. Set it in frontend/.env.local (see .env.example).",
    );
  }
  return url.replace(/\/$/, "");
}
