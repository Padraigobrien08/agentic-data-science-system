import type { PlanAlignmentFindingWire, TraceabilityWire } from "@/lib/ai-agents-meta";

function severityStyle(sev: string | undefined): string {
  if (sev === "high") {
    return "border-red-300 bg-red-50/90 text-red-950 dark:border-red-900 dark:bg-red-950/40 dark:text-red-100";
  }
  if (sev === "warning") {
    return "border-amber-300 bg-amber-50/80 text-amber-950 dark:border-amber-800 dark:bg-amber-950/30 dark:text-amber-100";
  }
  return "border-[var(--border)] bg-[var(--background)]/80 text-[var(--foreground)]";
}

function hasHighSeverity(findings: PlanAlignmentFindingWire[]): boolean {
  return findings.some((f) => f.severity === "high");
}

function hasMismatchCode(findings: PlanAlignmentFindingWire[]): boolean {
  return findings.some((f) => f.code === "plan_goal_mismatch");
}

type Props = {
  findings: PlanAlignmentFindingWire[];
  codes?: string[];
  /** Larger title + risk strip for planning section */
  variant?: "prominent" | "compact";
};

/**
 * Typed deterministic plan–goal alignment (backend ``compute_plan_alignment_findings``).
 */
export function PlanAlignmentCallout({ findings, codes, variant = "compact" }: Props) {
  if (!findings.length) return null;

  const high = hasHighSeverity(findings);
  const mismatch = hasMismatchCode(findings);

  return (
    <div className="space-y-2">
      {variant === "prominent" ? (
        <div
          className={`rounded border px-3 py-2 ${
            high || mismatch
              ? "border-red-400 bg-red-50 dark:border-red-800 dark:bg-red-950/50"
              : "border-emerald-200 bg-emerald-50/50 dark:border-emerald-900 dark:bg-emerald-950/20"
          }`}
        >
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--foreground)]">
            {high || mismatch ? "Planning mismatch risk" : "Plan–goal check"}
          </p>
          <p className="mt-1 text-sm text-[var(--foreground)]">
            {high || mismatch
              ? "The deterministic critic flagged a possible mismatch between what you asked for and the template that ran. Review the items below."
              : "No high-severity plan–goal mismatches detected; see notes for minor alignment caveats."}
          </p>
        </div>
      ) : null}

      <div
        className={`rounded border p-2 ${
          variant === "prominent"
            ? "border-[var(--border)] bg-[var(--background)]/40"
            : "border-amber-200/80 bg-amber-50/50 dark:border-amber-900/60 dark:bg-amber-950/25"
        }`}
      >
        <p
          className={`text-[10px] font-semibold uppercase tracking-wide ${
            variant === "prominent" ? "text-[var(--muted)]" : "text-amber-900 dark:text-amber-200"
          }`}
        >
          {variant === "prominent" ? "Critic plan–goal alignment" : "Plan–goal alignment (deterministic)"}
        </p>
        {codes && codes.length > 0 ? (
          <p className="mt-1 font-mono text-[10px] text-[var(--muted)]">codes: {codes.join(", ")}</p>
        ) : null}
        <ul className="mt-2 space-y-2 text-xs">
          {findings.map((row, i) => (
            <li
              key={`${row.code ?? "x"}-${i}`}
              className={`rounded border p-2 ${severityStyle(row.severity)}`}
            >
              <span className="font-mono text-[10px]">
                {row.code}
                {row.severity ? <span className="opacity-80"> · {row.severity}</span> : null}
              </span>
              {row.detail ? (
                <p className="mt-1 whitespace-pre-wrap text-[13px] leading-snug">{row.detail}</p>
              ) : null}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

export function collectPlanAlignmentFindings(
  phaseOutput: Record<string, unknown> | null,
  traceCritic: TraceabilityWire["critic"] | undefined,
): { findings: PlanAlignmentFindingWire[]; codes: string[] } {
  const raw = phaseOutput?.plan_alignment_findings;
  const fromPhase = Array.isArray(raw) ? (raw as PlanAlignmentFindingWire[]) : [];
  const fromTrace = traceCritic?.plan_alignment_findings;
  const findings = fromPhase.length ? fromPhase : Array.isArray(fromTrace) ? fromTrace : [];
  const codesRaw = phaseOutput?.plan_alignment_codes;
  const codesFromPo = Array.isArray(codesRaw)
    ? codesRaw.filter((x): x is string => typeof x === "string")
    : [];
  const codes =
    codesFromPo.length > 0
      ? codesFromPo
      : Array.isArray(traceCritic?.plan_alignment_codes)
        ? traceCritic!.plan_alignment_codes!.filter((x): x is string => typeof x === "string")
        : [];
  return { findings, codes };
}
