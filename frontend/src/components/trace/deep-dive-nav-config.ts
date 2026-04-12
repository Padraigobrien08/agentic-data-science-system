/** Section anchors for the deep-dive (audit) page — keep in sync with ``run-trace-experience`` ids. */

export type DeepDiveNavItem = { href: string; label: string };

const LLM_USAGE: DeepDiveNavItem = { href: "#run-llm-usage", label: "LLM usage" };

const CORE: DeepDiveNavItem[] = [
  { href: "#run-overview", label: "Overview" },
  { href: "#run-goal-plan", label: "Goal & plan" },
  { href: "#run-execution", label: "Execution" },
  { href: "#run-timeline", label: "Timeline" },
  { href: "#run-model-calls", label: "Model calls" },
  { href: "#run-artifacts", label: "Artifacts" },
  { href: "#run-agents", label: "Critic & report" },
  { href: "#run-conclusions", label: "Report" },
  { href: "#run-audit-meta", label: "Prompts & usage" },
];

/**
 * @param includeLlmUsageAnchor Insert LLM usage after Overview (needs ``id="run-llm-usage"`` under audit meta or nested).
 */
export function deepDiveNavItems(includeLlmUsageAnchor: boolean): DeepDiveNavItem[] {
  if (!includeLlmUsageAnchor) return CORE;
  return [CORE[0], LLM_USAGE, ...CORE.slice(1)];
}
