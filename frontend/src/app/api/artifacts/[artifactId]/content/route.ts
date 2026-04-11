import { NextResponse } from "next/server";

import { bearerAuthHeaders } from "@/lib/auth/backend-auth";
import { getApiBaseUrl } from "@/lib/api/config";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

const ALLOWED_DISPOSITION = new Set(["auto", "inline", "attachment"]);

export async function GET(
  req: Request,
  context: { params: Promise<{ artifactId: string }> },
) {
  const { artifactId } = await context.params;
  if (!UUID_RE.test(artifactId)) {
    return NextResponse.json({ detail: "Invalid artifact id" }, { status: 400 });
  }

  const url = new URL(req.url);
  const raw = url.searchParams.get("disposition") ?? "auto";
  const disposition = ALLOWED_DISPOSITION.has(raw) ? raw : "auto";

  const base = getApiBaseUrl();
  const auth = await bearerAuthHeaders();
  const upstream = await fetch(
    `${base}/v1/artifacts/${artifactId}/content?disposition=${encodeURIComponent(disposition)}`,
    { cache: "no-store", headers: { ...auth } },
  );

  if (!upstream.ok) {
    const text = await upstream.text();
    const ct = upstream.headers.get("content-type") ?? "application/json";
    return new NextResponse(text, {
      status: upstream.status,
      headers: {
        "Content-Type": ct,
        "Cache-Control": "private, no-cache",
      },
    });
  }

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
  headers.set("Cache-Control", "private, no-cache");

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers,
  });
}
