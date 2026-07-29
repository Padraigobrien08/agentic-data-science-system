"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import type { AnalysisRunStatus } from "@/lib/api/types";
import { getRunStateBannerModel, shouldPollRunStatus, type RunStateBannerSurface } from "@/lib/run-status-copy";

const TONE_BOX: Record<
  NonNullable<ReturnType<typeof getRunStateBannerModel>>["tone"],
  string
> = {
  neutral:
    "border-[var(--border)] bg-[var(--surface)] text-[var(--foreground)]",
  sky: "border-sky-200 bg-sky-50/90 text-sky-950 dark:border-sky-900 dark:bg-sky-950/35 dark:text-sky-50",
  amber:
    "border-amber-200 bg-amber-50/90 text-amber-950 dark:border-amber-900 dark:bg-amber-950/35 dark:text-amber-50",
  orange:
    "border-orange-200 bg-orange-50/90 text-orange-950 dark:border-orange-900 dark:bg-orange-950/35 dark:text-orange-50",
  violet:
    "border-violet-200 bg-violet-50/90 text-violet-950 dark:border-violet-900 dark:bg-violet-950/35 dark:text-violet-50",
  red: "border-red-300 bg-red-50/90 text-red-950 dark:border-red-800 dark:bg-red-950/40 dark:text-red-50",
};

type Props = {
  status: AnalysisRunStatus;
  surface: RunStateBannerSurface;
  runAnswerHref: string;
};

export function RunStateBanner({ status, surface, runAnswerHref }: Props) {
  const router = useRouter();
  const model = getRunStateBannerModel(status, surface);

  useEffect(() => {
    if (!shouldPollRunStatus(status)) {
      return;
    }
    const id = setInterval(() => {
      router.refresh();
    }, 5000);
    return () => clearInterval(id);
  }, [status, router]);

  if (!model) {
    return null;
  }

  /** Trace header already links back to chat — avoid repeating the same CTA. */
  const cta =
    model.showOutcomeCta && surface === "trace" ? (
      <p className="mt-2 text-xs text-[var(--muted)]">
        <Link href={runAnswerHref} className="font-medium text-[var(--foreground)] underline">
          Return to chat
        </Link>{" "}
        for the compact answer.
      </p>
    ) : null;

  return (
    <div
      role="status"
      aria-live="polite"
      className={`rounded-lg border px-3 py-2.5 text-sm ${TONE_BOX[model.tone]}`}
    >
      <p className="font-medium text-[var(--foreground)]">{model.title}</p>
      <p className="mt-1 text-sm leading-relaxed text-[var(--foreground)]/90">{model.body}</p>
      {model.progressLine ? (
        <p className="mt-1.5 text-xs text-[var(--muted)]">{model.progressLine}</p>
      ) : null}
      {cta}
    </div>
  );
}
