import { NextResponse } from "next/server";

import { bearerAuthHeaders } from "@/lib/auth/backend-auth";
import { getApiBaseUrl } from "@/lib/api/config";

const UUID_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function GET(
  _req: Request,
  context: { params: Promise<{ artifactId: string }> },
) {
  const { artifactId } = await context.params;
  if (!UUID_RE.test(artifactId)) {
    return NextResponse.json({ detail: "Invalid artifact id" }, { status: 400 });
  }

  const base = getApiBaseUrl();
  const auth = await bearerAuthHeaders();
  const upstream = await fetch(`${base}/v1/artifacts/${artifactId}/preview`, {
    headers: { Accept: "application/json", ...auth },
    cache: "no-store",
  });

  const body = await upstream.text();
  const ct = upstream.headers.get("content-type") ?? "application/json";
  return new NextResponse(body, {
    status: upstream.status,
    headers: {
      "Content-Type": ct,
      "Cache-Control": "private, no-cache",
    },
  });
}
