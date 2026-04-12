"use client";

import Link from "next/link";
import { useActionState } from "react";
import { useFormStatus } from "react-dom";

import { registerAction, type RegisterState } from "@/actions/auth";

function SubmitButton() {
  const { pending } = useFormStatus();
  return (
    <button
      type="submit"
      disabled={pending}
      className="w-full rounded border border-[var(--border)] bg-[var(--foreground)] px-3 py-2 font-mono text-sm text-[var(--background)] disabled:opacity-50"
    >
      {pending ? "Creating account…" : "Create account"}
    </button>
  );
}

type Props = {
  nextPath: string;
};

const initial: RegisterState = {};

export function RegisterForm({ nextPath }: Props) {
  const [state, formAction] = useActionState(registerAction, initial);

  return (
    <form action={formAction} className="space-y-4 rounded border border-[var(--border)] p-4">
      <input type="hidden" name="next" value={nextPath} />
      {state.error ? (
        <p className="rounded border border-red-300 bg-red-50 px-2 py-1 font-mono text-xs text-red-900 dark:border-red-800 dark:bg-red-950 dark:text-red-100">
          {state.error}
        </p>
      ) : null}
      <label className="block space-y-1">
        <span className="text-xs font-medium text-[var(--muted)]">Display name (optional)</span>
        <input
          name="display_name"
          type="text"
          autoComplete="nickname"
          maxLength={256}
          className="w-full rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-[var(--muted)]">Email</span>
        <input
          name="email"
          type="email"
          autoComplete="email"
          required
          className="w-full rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm"
        />
      </label>
      <label className="block space-y-1">
        <span className="text-xs font-medium text-[var(--muted)]">Password</span>
        <input
          name="password"
          type="password"
          autoComplete="new-password"
          required
          minLength={10}
          maxLength={72}
          className="w-full rounded border border-[var(--border)] bg-transparent px-3 py-2 font-mono text-sm"
        />
        <span className="block text-[10px] text-[var(--muted)]">
          Minimum 10 characters (API enforces up to 72).
        </span>
      </label>
      <SubmitButton />
      <p className="text-center text-xs text-[var(--muted)]">
        Already have an account?{" "}
        <Link href="/login" className="font-mono underline">
          Sign in
        </Link>
      </p>
    </form>
  );
}
