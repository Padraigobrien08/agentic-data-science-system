"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import {
  createInvestigationAction,
  type CreateInvestigationState,
} from "@/actions/investigations";

const SAMPLE_CSV = `store,week,sales
north,2023-01,120
north,2023-02,138
north,2023-03,151
south,2023-01,90
south,2023-02,84
south,2023-03,77`;

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded-md border border-neutral-300 bg-neutral-900 px-4 py-2 text-sm font-medium text-white transition hover:bg-neutral-700 disabled:opacity-50 dark:border-neutral-700 dark:bg-neutral-100 dark:text-neutral-900 dark:hover:bg-white"
    >
      {pending ? "Running investigation…" : "Run investigation"}
    </button>
  );
}

const initial: CreateInvestigationState = {};

export function NewInvestigationForm({ projectId }: Readonly<{ projectId: string }>) {
  const action = createInvestigationAction.bind(null, projectId);
  const [state, formAction] = useActionState(action, initial);

  const field = "rounded-md border border-neutral-300 bg-transparent px-3 py-2 text-sm outline-none focus:border-neutral-500 dark:border-neutral-700";
  const label = "text-xs font-medium text-neutral-600 dark:text-neutral-300";

  return (
    <form action={formAction} className="space-y-5">
      {state.error ? (
        <p className="rounded-md border border-red-300 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-950/40 dark:text-red-300">
          {state.error}
        </p>
      ) : null}

      <label className="flex flex-col gap-1.5">
        <span className={label}>Goal — what should the investigation answer?</span>
        <input
          name="goal"
          required
          placeholder="Are sales trending up over time?"
          className={field}
        />
      </label>

      <label className="flex flex-col gap-1.5">
        <span className={label}>Dataset (CSV — a header row plus data rows)</span>
        <textarea
          name="csv"
          required
          rows={10}
          defaultValue={SAMPLE_CSV}
          spellCheck={false}
          className={`${field} resize-y font-mono text-xs`}
        />
        <span className="text-xs text-neutral-400">
          The agent profiles the columns and picks its own experiments — no domain setup needed.
        </span>
      </label>

      <div className="grid gap-4 sm:grid-cols-3">
        <label className="flex flex-col gap-1.5">
          <span className={label}>Dataset name</span>
          <input name="name" placeholder="dataset" className={field} />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className={label}>Time column (optional)</span>
          <input name="time_field" placeholder="week" className={field} />
        </label>
        <label className="flex flex-col gap-1.5">
          <span className={label}>Entity columns (optional)</span>
          <input name="entity_id_fields" placeholder="store" className={field} />
        </label>
      </div>

      <label className="flex items-start gap-2 text-sm text-neutral-600 dark:text-neutral-300">
        <input type="checkbox" name="background" className="mt-0.5" />
        <span>
          Run in the background
          <span className="block text-xs text-neutral-400">
            Recommended for larger datasets. Requires a running worker; you can watch progress
            and land on the results when it finishes.
          </span>
        </span>
      </label>

      <div className="flex items-center gap-3">
        <SubmitButton />
      </div>
    </form>
  );
}
