const DEV_DEFAULT_API = "http://127.0.0.1:8000";

/**
 * Backend origin for server-side fetches (RSC, route handlers, server actions).
 * Not exposed to the browser — avoids depending on FastAPI CORS for mutations.
 */
export function getApiBaseUrl(): string {
  const url = process.env.API_URL?.trim();
  if (url) {
    return url.replace(/\/$/, "");
  }
  if (process.env.NODE_ENV === "development") {
    return DEV_DEFAULT_API;
  }
  throw new Error(
    "Missing API_URL. Set it in frontend/.env.local (see .env.example).",
  );
}
