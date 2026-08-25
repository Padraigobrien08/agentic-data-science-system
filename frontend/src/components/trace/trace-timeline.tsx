import type { TimelineEntry, TimelineGroup, TimelineTone } from "@/lib/trace-timeline";

/**
 * The one way a trace is drawn in this product.
 *
 * A gutter of groups, each a short run of entries with a glyph, a label, an optional tool
 * and the reason it happened. Both an investigation's decisions and an analysis run's steps
 * come through here, so learning to read one is learning to read both.
 */

const MONO = "font-mono text-[11px]";
const RULE = "border-[var(--border)]";

const TONE_INK: Record<TimelineTone, string> = {
  default: "text-[var(--foreground)]",
  notice: "text-[color:var(--status-info-ink)]",
  danger: "text-[color:var(--status-danger-ink)]",
};

/**
 * Two densities, one vocabulary.
 *
 * `compact` is the docked rail, where the trace shares its width with a conversation.
 * `comfortable` is a full page, which has room to put the group label in its own column
 * rather than stacking it. Same glyphs, same labels, same ordering — only the room differs,
 * so a reader moving between them is reading the same thing.
 */
export type TraceDensity = "compact" | "comfortable";

export function TraceTimeline({
  groups,
  emptyLabel = "No steps recorded.",
  density = "compact",
}: Readonly<{ groups: TimelineGroup[]; emptyLabel?: string; density?: TraceDensity }>) {
  if (!groups.length) {
    return <p className={`${MONO} text-[var(--chat-faint)]`}>{emptyLabel}</p>;
  }

  if (density === "comfortable") {
    return (
      <div>
        {groups.map((group) => (
          <div
            key={group.id}
            className={`grid gap-x-4 border-b ${RULE} py-4 sm:grid-cols-[104px_1fr]`}
          >
            <div>
              <p className={`${MONO} font-medium text-[var(--foreground)]`}>{group.label}</p>
              <p className={`mt-0.5 ${MONO} text-[var(--chat-faint)]`}>{group.meta}</p>
            </div>
            <ol className="mt-2 space-y-3 sm:mt-0">
              {group.entries.map((entry) => (
                <li key={entry.id}>
                  <Entry entry={entry} density="comfortable" />
                </li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    );
  }

  return (
    <ol className="space-y-0">
      {groups.map((group) => (
        <li key={group.id} className={`relative border-l ${RULE} pb-4 pl-4`}>
          <span
            className="absolute -left-[3px] top-1.5 h-1.5 w-1.5 rounded-full bg-[var(--chat-faint)]"
            aria-hidden
          />
          <p className={`${MONO} font-medium text-[var(--foreground)]`}>
            {group.label}
            {group.meta ? (
              <span className="font-normal text-[var(--chat-faint)]">
                {" · "}
                {group.meta}
              </span>
            ) : null}
          </p>
          <div className="mt-2 space-y-2">
            {group.entries.map((entry) => (
              <Entry key={entry.id} entry={entry} density="compact" />
            ))}
          </div>
        </li>
      ))}
    </ol>
  );
}

/**
 * One act in the trace. A callout replaces the row when several records are really one
 * event — the only case where the trace departs from one row per record.
 */
function Entry({ entry, density }: Readonly<{ entry: TimelineEntry; density: TraceDensity }>) {
  const roomy = density === "comfortable";

  if (entry.callout) {
    return (
      <div className={`rounded-md border ${RULE} bg-[var(--chat-accent-soft)] p-2.5`}>
        <p className={`${MONO} uppercase tracking-[0.08em] text-[color:var(--status-info-ink)]`}>
          {entry.callout.heading}
        </p>
        <p
          className={`mt-1 leading-snug text-[var(--foreground)] ${
            roomy ? "text-sm" : "text-[12.5px]"
          }`}
        >
          {entry.callout.body}
        </p>
        {entry.callout.items?.length ? (
          <div className="mt-2 space-y-1">
            {entry.callout.items.map((item) => (
              <p
                key={item.id}
                className={`border-l pl-3 ${RULE} leading-snug text-[var(--muted)] ${
                  roomy ? "text-[13px]" : "text-[12px]"
                }`}
              >
                {item.text}
                {item.meta ? (
                  <span className={`${MONO} ml-2 text-[var(--chat-faint)]`}>{item.meta}</span>
                ) : null}
              </p>
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  return (
    <div className={`flex ${roomy ? "gap-3" : "gap-2"}`}>
      <span
        className={`${MONO} select-none ${roomy ? "mt-0.5" : ""} ${
          entry.tone && entry.tone !== "default" ? TONE_INK[entry.tone] : "text-[var(--chat-faint)]"
        }`}
        aria-hidden
      >
        {entry.glyph}
      </span>
      <div className="min-w-0 flex-1">
        <p
          className={`leading-snug ${roomy ? "text-sm font-medium" : "text-[12.5px]"} ${
            TONE_INK[entry.tone ?? "default"]
          }`}
        >
          {entry.label}
          {entry.accent ? (
            <span
              className={`${MONO} ${roomy ? "ml-2 font-normal" : "ml-1.5"} text-[var(--accent)]`}
            >
              {roomy ? "→ " : ""}
              {entry.accent}
            </span>
          ) : null}
        </p>
        {entry.detail ? (
          <p
            className={`leading-snug text-[var(--muted)] ${
              roomy ? "text-sm" : "mt-0.5 text-[11.5px]"
            }`}
          >
            {entry.detail}
          </p>
        ) : null}
      </div>
    </div>
  );
}
