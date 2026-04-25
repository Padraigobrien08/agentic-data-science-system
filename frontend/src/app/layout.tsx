import type { Metadata } from "next";

import { SiteHeader } from "@/components/layout/site-header";
import { getCurrentUser } from "@/lib/auth/session";

import "./globals.css";

export const metadata: Metadata = {
  title: "EDGAR Analysis",
  description: "Evidence-first SEC analysis with deterministic runs, artifacts, and traceable workflows",
  icons: {
    icon: [{ url: "/favicon.svg", type: "image/svg+xml" }],
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const user = await getCurrentUser();
  return (
    <html lang="en" data-scroll-behavior="smooth">
      <body className="min-h-screen antialiased">
        <SiteHeader user={user} />
        <main className="mx-auto w-full max-w-[90rem] px-3 py-8 sm:px-5 lg:px-6">{children}</main>
      </body>
    </html>
  );
}
