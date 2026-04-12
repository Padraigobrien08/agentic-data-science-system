"use client";

import { useFormState, useFormStatus } from "react-dom";

import { AnalysisComposerFields } from "@/components/analysis/analysis-composer-fields";
import { createAnalysisRunForm } from "@/actions/runs";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      aria-busy={pending}
      className="rounded-lg bg-[var(--foreground)] px-5 py-2.5 text-sm font-semibold text-[var(--background)] transition-opacity hover:opacity-90 disabled:opacity-50"
    >
      {pending ? "Creating run…" : "Create run"}
    </button>
  );
}

type Props = {
  projectId: string;
};

export function NewRunForm({ projectId }: Props) {
  const action = createAnalysisRunForm.bind(null, projectId);
  const [state, formAction] = useFormState(action, {});

  return (
    <form action={formAction} className="max-w-2xl space-y-6">
      {state.error ? (
        <div
          role="alert"
          className="rounded-lg border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-100"
        >
          {state.error}
        </div>
      ) : null}

      <div className="rounded-xl border border-[var(--border)] bg-[var(--background)] p-4 shadow-sm sm:p-5">
        <AnalysisComposerFields variant="project" idPrefix="new-run" />
      </div>

      <fieldset className="space-y-3 rounded-xl border border-[var(--border)] px-4 py-3">
        <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Options
        </legend>
        <label className="flex items-center gap-2 text-sm text-[var(--foreground)]">
          <input type="checkbox" name="refresh" className="rounded border-[var(--border)]" />
          <span>
            Refresh SEC cache{" "}
            <span className="text-xs text-[var(--muted)]">(re-fetch filings used in panels)</span>
          </span>
        </label>
        <label className="flex items-start gap-2 text-sm text-[var(--foreground)]">
          <input type="checkbox" name="execute_now" className="mt-0.5 rounded border-[var(--border)]" />
          <span>
            <strong className="font-medium">Run immediately</strong>{" "}
            <span className="text-xs text-[var(--muted)]">
              — waits for the pipeline to finish in this request (can take several minutes).
            </span>
          </span>
        </label>
        <label className="flex items-start gap-2 text-sm text-[var(--foreground)]">
          <input type="checkbox" name="enqueue_execution" className="mt-0.5 rounded border-[var(--border)]" />
          <span>
            <strong className="font-medium">Queue for worker</strong>{" "}
            <span className="text-xs text-[var(--muted)]">
              — create the run now; a background job executes the pipeline. Do not use with “Run immediately”.
            </span>
          </span>
        </label>
      </fieldset>

      <details className="text-xs text-[var(--muted)]">
        <summary className="cursor-pointer font-medium text-[var(--foreground)]">API mapping</summary>
        <p className="mt-2">
          Goal → <code className="font-mono text-[var(--foreground)]">orchestration_goal_text</code> and{" "}
          <code className="font-mono text-[var(--foreground)]">input_payload_json.analysis_goal</code>. Tickers →{" "}
          <code className="font-mono text-[var(--foreground)]">input_payload_json.tickers</code>.
        </p>
      </details>

      <SubmitButton />
    </form>
  );
}
