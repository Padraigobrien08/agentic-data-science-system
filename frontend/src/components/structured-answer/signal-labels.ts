const WEAK_EVIDENCE_LABELS: Record<string, string> = {
  low_overall_confidence: "Low overall confidence",
  flagged_issues: "Critic flagged issues",
  plan_alignment_high_severity: "Plan alignment: high severity",
  plan_alignment_flags: "Plan alignment flags",
  thin_panel: "Thin evidence panel",
};

/** Turn persisted ``weak_evidence_signals`` ids into short UI labels. */
export function humanizeWeakEvidenceSignal(id: string): string {
  const k = id.trim();
  if (!k) return id;
  return WEAK_EVIDENCE_LABELS[k] ?? titleCaseSnake(k);
}

function titleCaseSnake(s: string): string {
  return s
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}
