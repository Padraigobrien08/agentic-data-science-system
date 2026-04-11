import type { ReactNode } from "react";

import { MetaRow } from "@/components/ui/technical";

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === "object" && v !== null && !Array.isArray(v);
}

function stringList(v: unknown, max: number): string[] {
  if (!Array.isArray(v)) return [];
  return v.filter((x): x is string => typeof x === "string").slice(0, max);
}

type Props = {
  /** From phase_output.planning_transparency or traceability.intent.planning_transparency */
  transparency: unknown;
};

/**
 * Structured plan decision: template, preferences, prioritized vs de-emphasized signals.
 * No model chain-of-thought — rule-derived summaries only.
 */
export function PlanningTransparencyPanel({ transparency }: Props): ReactNode {
  if (!isRecord(transparency) || transparency.present === false) {
    return (
      <p className="text-sm text-[var(--muted)]">
        No structured planning transparency on this run (planning may have failed or predates this
        contract).
      </p>
    );
  }

  const rationale =
    typeof transparency.planning_rationale_summary === "string"
      ? transparency.planning_rationale_summary
      : null;
  const templateId =
    typeof transparency.plan_template_id === "string" ? transparency.plan_template_id : null;
  const goalCode = typeof transparency.goal_code === "string" ? transparency.goal_code : null;
  const orchIntent =
    typeof transparency.orchestration_intent === "string" ? transparency.orchestration_intent : null;
  const understood =
    typeof transparency.what_we_understood === "string" ? transparency.what_we_understood : null;
  const echo =
    typeof transparency.user_goal_echo_excerpt === "string"
      ? transparency.user_goal_echo_excerpt
      : null;
  const emphasized = stringList(transparency.emphasized, 14);
  const deemphasized = stringList(transparency.deemphasized, 14);

  const prefs = isRecord(transparency.selected_signal_preferences)
    ? transparency.selected_signal_preferences
    : null;

  const flatPriority =
    typeof transparency.priority_metrics !== "undefined"
      ? stringList(transparency.priority_metrics, 8)
      : prefs && Array.isArray(prefs.priority_metrics)
        ? stringList(prefs.priority_metrics, 8)
        : [];

  const directional =
    typeof transparency.directional_focus === "string"
      ? transparency.directional_focus
      : prefs && typeof prefs.directional_focus === "string"
        ? prefs.directional_focus
        : null;
  const signalStyle =
    typeof transparency.preferred_signal_style === "string"
      ? transparency.preferred_signal_style
      : prefs && typeof prefs.preferred_signal_style === "string"
        ? prefs.preferred_signal_style
        : null;
  const peerReq =
    typeof transparency.peer_requirement === "string"
      ? transparency.peer_requirement
      : prefs && typeof prefs.peer_requirement === "string"
        ? prefs.peer_requirement
        : null;
  const timeFocus =
    typeof transparency.time_focus === "string"
      ? transparency.time_focus
      : prefs && typeof prefs.time_focus === "string"
        ? prefs.time_focus
        : null;
  const primaryMode =
    typeof transparency.primary_analysis_mode === "string"
      ? transparency.primary_analysis_mode
      : prefs && typeof prefs.primary_analysis_mode === "string"
        ? prefs.primary_analysis_mode
        : null;

  const rules = stringList(transparency.intent_rules_matched, 12);

  const signalStyleLabel =
    signalStyle === "persistent"
      ? "Persistent (multi-period stress)"
      : signalStyle === "one_off"
        ? "One-off (point-in-time / |z|)"
        : signalStyle ?? null;

  return (
    <div className="space-y-0 border-t border-[var(--border)] pt-3">
      {templateId || signalStyle || directional ? (
        <div className="mb-3 flex flex-wrap items-center gap-2 rounded border border-[var(--border)] bg-[var(--background)]/50 px-3 py-2">
          <span className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Plan snapshot
          </span>
          {templateId ? (
            <code className="rounded bg-indigo-100/80 px-1.5 py-0.5 font-mono text-[11px] text-indigo-950 dark:bg-indigo-950/60 dark:text-indigo-100">
              {templateId}
            </code>
          ) : null}
          {signalStyle ? (
            <span
              className={`rounded px-2 py-0.5 font-mono text-[11px] ${
                signalStyle === "persistent"
                  ? "bg-emerald-100 text-emerald-950 dark:bg-emerald-950/50 dark:text-emerald-100"
                  : signalStyle === "one_off"
                    ? "bg-violet-100 text-violet-950 dark:bg-violet-950/50 dark:text-violet-100"
                    : "bg-[var(--border)]/60 text-[var(--foreground)]"
              }`}
              title="preferred_signal_style — persistent vs one-off emphasis"
            >
              signal: {signalStyle}
            </span>
          ) : null}
          {directional ? (
            <span className="rounded bg-amber-100/90 px-2 py-0.5 font-mono text-[11px] text-amber-950 dark:bg-amber-950/40 dark:text-amber-100">
              direction: {directional}
            </span>
          ) : null}
        </div>
      ) : null}

      {rationale ? (
        <div className="mb-3 rounded border border-[var(--border)] bg-[var(--background)]/60 p-3">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-[var(--muted)]">
            Planning rationale (rule-derived)
          </p>
          <p className="mt-2 max-w-prose whitespace-pre-wrap text-sm leading-relaxed">{rationale}</p>
        </div>
      ) : null}

      {templateId ? <MetaRow label="plan_template_id">{templateId}</MetaRow> : null}
      {orchIntent ? (
        <MetaRow label="orchestration_intent (coarse)">{orchIntent}</MetaRow>
      ) : null}
      {goalCode ? <MetaRow label="goal_code (template)">{goalCode}</MetaRow> : null}
      {primaryMode ? <MetaRow label="primary_analysis_mode">{primaryMode}</MetaRow> : null}
      {flatPriority.length > 0 ? (
        <MetaRow label="priority_metrics">{flatPriority.join(", ")}</MetaRow>
      ) : null}
      {directional ? <MetaRow label="directional_focus">{directional}</MetaRow> : null}
      {signalStyle ? (
        <MetaRow label="signal_style (persistent vs one-off)">
          {signalStyleLabel ?? signalStyle}
        </MetaRow>
      ) : null}
      {peerReq ? <MetaRow label="peer_requirement">{peerReq}</MetaRow> : null}
      {timeFocus ? <MetaRow label="time_focus">{timeFocus}</MetaRow> : null}

      {understood ? (
        <MetaRow label="what_we_understood">
          <span className="whitespace-pre-wrap">{understood}</span>
        </MetaRow>
      ) : null}
      {echo ? (
        <MetaRow label="user_goal_echo_excerpt">
          <span className="whitespace-pre-wrap">{echo}</span>
        </MetaRow>
      ) : null}

      {rules.length > 0 ? (
        <MetaRow label="intent_rules_matched">
          <span className="font-mono text-[11px]">{rules.join(", ")}</span>
        </MetaRow>
      ) : null}

      {emphasized.length > 0 ? (
        <div className="border-t border-[var(--border)] py-2">
          <p className="text-[10px] font-semibold uppercase text-emerald-800 dark:text-emerald-300">
            Prioritized
          </p>
          <ul className="mt-1 list-inside list-disc text-sm text-[var(--foreground)]">
            {emphasized.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}

      {deemphasized.length > 0 ? (
        <div className="border-t border-[var(--border)] py-2">
          <p className="text-[10px] font-semibold uppercase text-[var(--muted)]">De-emphasized</p>
          <ul className="mt-1 list-inside list-disc text-sm text-[var(--muted)]">
            {deemphasized.map((x) => (
              <li key={x}>{x}</li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}
