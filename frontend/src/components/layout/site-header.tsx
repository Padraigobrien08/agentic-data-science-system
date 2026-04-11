import Link from "next/link";

export function SiteHeader() {
  return (
    <header className="border-b border-[var(--border)] bg-[var(--background)]">
      <div className="mx-auto flex h-12 max-w-5xl items-center gap-6 px-4">
        <Link href="/" className="font-semibold text-[var(--foreground)]">
          EDGAR Analysis
        </Link>
        <span className="text-sm text-[var(--muted)]">Local scaffold</span>
      </div>
    </header>
  );
}
