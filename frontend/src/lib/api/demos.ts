import "server-only";

import type { DemoCapture, DemoChatThread } from "@/lib/demo-static/capture-types";
import {
  DEMO_ARTIFACT_HREFS,
  DEMO_CAPTURES,
  DEMO_DETAILS,
  DEMO_INDEX,
} from "@/lib/demo-static/generated";

import { apiGet } from "./client";
import { ApiError } from "./errors";
import type { InvestigationDetail, InvestigationSummary } from "./types";

/**
 * The one seam between the two demo data sources
 * (docs/decisions/2026-08-14-static-replay-showcase.md, D9).
 *
 * Static mode serves the committed export of the published demos; live mode proxies
 * `/v1/demos*`. Pages never branch on the mode themselves — when the live backend exists,
 * setting API_URL flips the whole surface. DEMO_STATIC=1/0 overrides for local testing.
 */
export function staticShowcase(): boolean {
  const override = process.env.DEMO_STATIC?.trim();
  if (override === "1") return true;
  if (override === "0") return false;
  return process.env.NODE_ENV === "production" && !process.env.API_URL?.trim();
}

/** Published demos, oldest first — same ordering as GET /v1/demos. */
export async function listDemos(): Promise<InvestigationSummary[]> {
  if (staticShowcase()) {
    return DEMO_INDEX;
  }
  return apiGet<InvestigationSummary[]>("/v1/demos");
}

/** One published demo in full, or null when the slug is not published. */
export async function getDemo(slug: string): Promise<InvestigationDetail | null> {
  if (staticShowcase()) {
    return DEMO_DETAILS[slug] ?? null;
  }
  try {
    return await apiGet<InvestigationDetail>(`/v1/demos/${encodeURIComponent(slug)}`);
  } catch (e) {
    if (e instanceof ApiError && e.status === 404) {
      return null;
    }
    throw e;
  }
}

/**
 * The model calls and chat turns behind a published demo, or null when unavailable.
 *
 * Unlike the rest of this module there is no live counterpart: raw model payloads are
 * admin-gated on `/v1` (`require_admin_debug_access`), and publishing a demo is a separate
 * deliberate act over a run an operator chose to expose. So the bundle ships only with the
 * static export, and callers must treat null as normal rather than as an error.
 */
export async function getDemoCapture(slug: string): Promise<DemoCapture | null> {
  if (!staticShowcase()) {
    return null;
  }
  return DEMO_CAPTURES[slug] ?? null;
}

/**
 * The conversation recorded against a published demo.
 *
 * Unlike the capture bundle above this *does* have a live counterpart: the turns are not
 * the sensitive part, and a deployment with a backend was otherwise unable to show the
 * question a run was asked — every demo opened on an answer to an invisible question.
 * Static mode reads the same turns out of the committed capture.
 */
export async function getDemoChat(slug: string): Promise<DemoChatThread[]> {
  if (staticShowcase()) {
    return DEMO_CAPTURES[slug]?.chat ?? [];
  }
  try {
    return await apiGet<DemoChatThread[]>(`/v1/demos/${encodeURIComponent(slug)}/chat`);
  } catch {
    // A recorded run is still worth showing without its prompt; the caller falls back to
    // stating the goal rather than inventing a question.
    return [];
  }
}

/**
 * Download href for an artifact behind a published demo, or null when the bytes are not
 * available (blob pruned, or an artifact the export skipped).
 */
export function demoArtifactHref(slug: string, artifactId: string): string | null {
  if (staticShowcase()) {
    return DEMO_ARTIFACT_HREFS[slug]?.[artifactId] ?? null;
  }
  return `/api/demos/${encodeURIComponent(slug)}/artifacts/${encodeURIComponent(artifactId)}/content`;
}
