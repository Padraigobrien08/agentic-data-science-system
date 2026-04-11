import Link from "next/link";
import { redirect } from "next/navigation";

import { RegisterForm } from "@/components/auth/register-form";
import { getCurrentUser } from "@/lib/auth/session";

export const dynamic = "force-dynamic";

export default async function RegisterPage({
  searchParams,
}: Readonly<{
  searchParams: Promise<{ next?: string }>;
}>) {
  const { next } = await searchParams;
  const user = await getCurrentUser();
  if (user) {
    redirect(next?.startsWith("/") && !next.startsWith("//") ? next : "/projects");
  }

  const nextPath = next?.startsWith("/") && !next.startsWith("//") ? next : "/projects";

  return (
    <div className="mx-auto max-w-md space-y-6">
      <div>
        <h1 className="text-lg font-semibold">Create account</h1>
        <p className="mt-1 text-xs text-[var(--muted)]">
          Calls <code className="text-[var(--foreground)]">POST /v1/auth/register</code>, then signs you
          in with the same credentials. Open registration can be disabled on the server (
          <code className="text-[var(--foreground)]">EDGAR_BACKEND_ALLOW_OPEN_REGISTRATION=false</code>
          ).
        </p>
      </div>
      <RegisterForm nextPath={nextPath} />
      <Link href="/login" className="block font-mono text-xs underline">
        ← Sign in instead
      </Link>
    </div>
  );
}
