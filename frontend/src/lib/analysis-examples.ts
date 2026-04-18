/** Curated examples — aligned with SEC panel / peer / margin style analyses the planner supports. */

export type AnalysisExample = {
  label: string;
  goal: string;
  /** Comma-separated tickers */
  tickers: string;
};

export const ANALYSIS_EXAMPLES: AnalysisExample[] = [
  {
    label: "Peer comparison",
    goal:
      "AAPL versus MSFT: which company is weaker on operating margin and free cash flow margin over the last eight quarters?",
    tickers: "AAPL, MSFT",
  },
  {
    label: "Anomaly screen",
    goal:
      "Flag unusual one-off moves in cash flow and operating margins; de-emphasize single-quarter noise and call out sustained vs transient patterns.",
    tickers: "AAPL, MSFT, NVDA",
  },
  {
    label: "Deterioration trend",
    goal:
      "Assess whether margin pressure is temporary or structural for NVDA over the last eight quarters; prioritize sustained patterns over one-off spikes.",
    tickers: "NVDA",
  },
  {
    label: "Cash flow quality",
    goal:
      "Assess cash conversion versus net income and capex intensity; call out working-capital swings and whether cash flow quality improved or worsened year over year.",
    tickers: "AAPL",
  },
];

/**
 * Optional one-click additions — short phrases the intent/planning stack can interpret well.
 * (See planning transparency: time horizon, peers, metrics, de-emphasis.)
 */
export type GoalSnippet = { id: string; label: string; append: string };

export const GOAL_SNIPPETS: GoalSnippet[] = [
  { id: "horizon", label: "+ Last 8 quarters", append: "Focus on the last eight quarters." },
  { id: "peers", label: "+ Compare to peers", append: "Compare results to relevant peers or the sector median where data allows." },
  { id: "metrics", label: "+ Margins & FCF", append: "Emphasize operating margin, gross margin, and free cash flow conversion." },
  { id: "direction", label: "+ Direction of change", append: "Stress direction of change (improving vs deteriorating), not just levels." },
  { id: "noise", label: "+ Ignore one-offs", append: "De-emphasize one-off restructuring and non-recurring items when possible." },
  { id: "rank", label: "+ Rank vs absolute", append: "Prefer percentile or rank vs peers over absolute size alone." },
];

export function parseTickerString(raw: string): string[] {
  return raw
    .split(/[\n,\s]+/)
    .map((s) => s.trim().toUpperCase().replace(/[^A-Z0-9.-]/g, ""))
    .filter(Boolean);
}
