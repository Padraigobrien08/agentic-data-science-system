"use client";

import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { createProjectAction, type CreateProjectState } from "@/actions/projects";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="rounded border border-[var(--border)] bg-[var(--foreground)] px-3 py-1.5 font-mono text-xs text-[var(--background)] disabled:opacity-50"
    >
      {pending ? "Creating…" : "Create"}
    </button>
  );
}

const initial: CreateProjectState = {};

export function CreateProjectForm() {
  const [state, formAction] = useActionState(createProjectAction, initial);

  return (
    <form action={formAction} className="flex flex-col gap-3">
      {state.error ? (
        <p className="w-full font-mono text-xs text-red-700 dark:text-red-400">{state.error}</p>
      ) : null}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end">
        <label className="flex min-w-[12rem] flex-1 flex-col gap-1">
          <span className="text-[10px] text-[var(--muted)]">chat title (optional)</span>
          <input
            name="name"
            placeholder="MSFT focus chat"
            className="rounded border border-[var(--border)] bg-transparent px-2 py-1.5 font-mono text-sm"
          />
        </label>
        <SubmitButton />
      </div>
      <label className="flex flex-col gap-1">
        <span className="text-[10px] text-[var(--muted)]">tickers (comma or newline separated)</span>
        <textarea
          name="tickers"
          required
          rows={3}
          placeholder="AAPL, MSFT, NVDA"
          className="resize-y rounded border border-[var(--border)] bg-transparent px-2 py-1.5 font-mono text-sm"
        />
      </label>
    </form>
  );
}
