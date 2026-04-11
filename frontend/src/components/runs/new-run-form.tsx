"use client";

import { useFormState, useFormStatus } from "react-dom";

import { createAnalysisRunForm } from "@/actions/runs";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded border border-[var(--border)] bg-[var(--foreground)] px-4 py-2 font-mono text-sm text-[var(--background)] disabled:opacity-50"
    >
      {pending ? "Submitting…" : "Submit run"}
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
          className="rounded border border-red-300 bg-red-50 p-3 font-mono text-sm text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100"
        >
          {state.error}
        </div>
      ) : null}

      <fieldset className="space-y-4 rounded border border-[var(--border)] p-4">
        <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Request
        </legend>
        <p className="text-xs text-[var(--muted)]">
          Maps to <code className="text-[var(--foreground)]">POST /v1/runs</code> body fields{" "}
          <code className="text-[var(--foreground)]">orchestration_goal_text</code> and{" "}
          <code className="text-[var(--foreground)]">input_payload_json</code>.
        </p>
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Analysis goal</span>
          <textarea
            name="goal"
            required
            rows={4}
            className="rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm"
            placeholder="Natural-language goal passed to orchestration"
          />
        </label>
        <label className="flex flex-col gap-1">
          <span className="text-sm font-medium">Tickers</span>
          <span className="text-xs text-[var(--muted)]">
            Comma or newline separated → <code>input_payload_json.tickers</code>
          </span>
          <textarea
            name="tickers"
            rows={3}
            className="rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm uppercase"
            placeholder="AAPL&#10;MSFT"
          />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" name="refresh" className="rounded border-[var(--border)]" />
          <span>
            Refresh SEC cache{" "}
            <span className="text-xs text-[var(--muted)]">(input_payload_json.refresh)</span>
          </span>
        </label>
      </fieldset>

      <fieldset className="space-y-3 rounded border border-[var(--border)] p-4">
        <legend className="px-1 text-xs font-semibold uppercase tracking-wide text-[var(--muted)]">
          Execution
        </legend>
        <p className="text-xs text-[var(--muted)]">
          Default: create row only (<code>pending</code>). Use one of the options below.
        </p>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            name="execute_now"
            className="mt-1 rounded border-[var(--border)]"
          />
          <span>
            <strong>Execute now</strong> — calls{" "}
            <code className="text-xs">POST /v1/runs/&#123;id&#125;/execute</code> synchronously
            after create (may take minutes).
          </span>
        </label>
        <label className="flex items-start gap-2 text-sm">
          <input
            type="checkbox"
            name="enqueue_execution"
            className="mt-1 rounded border-[var(--border)]"
          />
          <span>
            <strong>Queue for worker</strong> — sets{" "}
            <code className="text-xs">enqueue_execution: true</code> on create; background job runs
            the pipeline.
          </span>
        </label>
      </fieldset>

      <SubmitButton />
    </form>
  );
}
