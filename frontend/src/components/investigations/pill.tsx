import type { Tone } from "@/lib/investigation-view";

/** A small rounded status/tone pill. */
export function Pill({ tone }: Readonly<{ tone: Tone }>) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${tone.className}`}
    >
      {tone.label}
    </span>
  );
}
