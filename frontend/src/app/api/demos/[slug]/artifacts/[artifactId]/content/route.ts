import { NextResponse } from "next/server";

import { getApiBaseUrl } from "@/lib/api/config";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const SLUG_RE = /^[a-z0-9]+(?:-[a-z0-9]+)*$/;

/**
 * Live-mode proxy for artifact bytes behind a published demo. Unauthenticated on purpose —
 * the backend's publication check is the authorization (backend/api/routes/demos.py). In
 * static-showcase mode this route is never linked; blobs are served from /demo-data instead.
 */
export async function GET(
  _req: Request,
  context: { params: Promise<{ slug: string; artifactId: string }> },
) {
  const { slug, artifactId } = await context.params;
  if (!SLUG_RE.test(slug) || !UUID_RE.test(artifactId)) {
    return NextResponse.json({ detail: "Invalid demo artifact reference" }, { status: 400 });
  }

  const base = getApiBaseUrl();
  const upstream = await fetch(
    `${base}/v1/demos/${slug}/artifacts/${artifactId}/content?disposition=attachment`,
    { cache: "no-store" },
  );

  const headers = new Headers();
  const forward = [
    "content-type",
    "content-disposition",
    "content-length",
    "etag",
    "x-content-type-options",
  ] as const;
  for (const name of forward) {
    const v = upstream.headers.get(name);
    if (v) headers.set(name, v);
  }
  // Published demos are frozen; let intermediaries cache the bytes.
  headers.set("Cache-Control", "public, max-age=3600");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers,
  });
}
