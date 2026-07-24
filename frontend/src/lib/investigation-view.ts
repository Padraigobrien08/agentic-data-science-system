/**
 * Pure view helpers for the investigation read surfaces.
 *
 * No React, no data fetching — just deterministic mappings from persisted
 * investigation state to display labels and Tailwind tone classes, so the
 * components stay declarative and these can be unit-tested in isolation.
 */

import type {
  EvidenceItem,
  HypothesisItem,
  InvestigationDetail,
} from "@/lib/api/types";

export interface Tone {
  label: string;
  className: string;
}

const NEUTRAL = "bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300";
const GREEN = "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300";
const AMBER = "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300";
const RED = "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300";
const BLUE = "bg-sky-100 text-sky-800 dark:bg-sky-900/40 dark:text-sky-300";

export function investigationStatusTone(status: string): Tone {
  switch (status) {
    case "converged":
      return { label: "Converged", className: GREEN };
    case "running":
    case "planning":
    case "awaiting_evidence":
      return { label: titleize(status), className: BLUE };
    case "exhausted":
      return { label: "Exhausted", className: AMBER };
    case "failed":
      return { label: "Failed", className: RED };
    default:
      return { label: titleize(status), className: NEUTRAL };
  }
}

export function hypothesisStatusTone(status: string): Tone {
  switch (status) {
    case "supported":
      return { label: "Supported", className: GREEN };
    case "weakened":
      return { label: "Weakened", className: AMBER };
    case "rejected":
      return { label: "Rejected", className: RED };
    case "unresolved":
      return { label: "Unresolved", className: NEUTRAL };
    default:
      return { label: titleize(status), className: BLUE };
  }
}

export function dispositionTone(disposition: string): Tone {
  switch (disposition) {
    case "supported":
      return { label: "Supported", className: GREEN };
    case "refuted":
      return { label: "Refuted", className: RED };
    case "inconclusive":
      return { label: "Inconclusive", className: AMBER };
    case "insufficient_evidence":
      return { label: "Insufficient evidence", className: NEUTRAL };
    default:
      return { label: titleize(disposition), className: NEUTRAL };
  }
}

export function evidenceDirectionTone(direction: string): Tone {
  switch (direction) {
    case "supports":
      return { label: "Supports", className: GREEN };
    case "refutes":
      return { label: "Refutes", className: RED };
    case "neutral":
      return { label: "Neutral", className: NEUTRAL };
    default:
      return { label: titleize(direction), className: NEUTRAL };
  }
}

/** Format a 0..1 confidence as a whole-percent string; null/NaN → "—". */
export function formatConfidence(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  const clamped = Math.max(0, Math.min(1, value));
  return `${Math.round(clamped * 100)}%`;
}

export function titleize(value: string): string {
  return value
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

/** Evidence linked to a given hypothesis id (either direction). */
export function evidenceForHypothesis(
  detail: InvestigationDetail,
  hypothesis: HypothesisItem,
): EvidenceItem[] {
  return detail.evidence.filter((e) => e.hypothesis_ids.includes(hypothesis.id));
}

/** Confidence delta (posterior − prior) for a hypothesis, or null when unchanged. */
export function confidenceDelta(h: HypothesisItem): number | null {
  const delta = h.confidence - h.prior_confidence;
  return Math.abs(delta) < 1e-9 ? null : delta;
}
