"use client";

import { useActionState } from "react";

import { submitInterestAction, type InterestState } from "@/actions/auth";

/**
 * Optional email capture — a signal of interest, not a sign-up.
 *
 * The only client component on the landing page: it exists because the result
 * has to render in place without a navigation. It posts to `/v1/interest`, so
 * the caller mounts it only when a live backend is actually there (never in the
 * static export, where the request has nowhere to land).
 */
export function InterestForm() {
  const [interest, interestAction, pending] = useActionState(
    submitInterestAction,
    {} as InterestState,
  );

  if (interest.ok) {
    return (
      <p className="text-[12.5px] text-[var(--ld-green)]" role="status">
        Thanks — we&rsquo;ll keep you posted.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2.5">
      <form action={interestAction} className="flex flex-wrap items-center gap-2.5">
        <input
          name="email"
          type="email"
          required
          placeholder="you@work.com"
          aria-label="Email for product updates"
          className="h-10 w-full min-w-[15rem] flex-1 rounded-lg border border-white/20 bg-white/[0.022] px-3.5 text-sm text-[var(--ld-ink)] outline-none transition placeholder:text-[var(--ld-dim)] hover:border-white/30 focus:border-[var(--ld-blue)] sm:w-auto"
        />
        <button
          type="submit"
          disabled={pending}
          className="inline-flex h-10 items-center whitespace-nowrap rounded-lg border border-white/20 px-[18px] text-sm text-[var(--ld-ink)] transition hover:border-white/40 hover:bg-white/5 disabled:opacity-50"
        >
          {pending ? "Sending…" : "Keep me posted"}
        </button>
      </form>
      {interest.error ? (
        <p className="text-[12.5px] text-[var(--ld-red)]" role="alert">
          {interest.error}
        </p>
      ) : (
        <p className="text-[12.5px] text-[var(--ld-dim)]">
          No sign-up required. Email is optional — just a signal of interest.
        </p>
      )}
    </div>
  );
}
