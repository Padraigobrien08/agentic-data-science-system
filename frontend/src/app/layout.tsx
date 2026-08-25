import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { AppChrome } from "@/components/layout/app-chrome";
import { getCurrentUser } from "@/lib/auth/session";

import "./globals.css";

import { PRODUCT_NAME, PRODUCT_TAGLINE } from "@/lib/brand";

const geistSans = Geist({ subsets: ["latin"], variable: "--font-geist-sans", display: "swap" });
const geistMono = Geist_Mono({ subsets: ["latin"], variable: "--font-geist-mono", display: "swap" });

export const metadata: Metadata = {
  title: PRODUCT_NAME,
  description: PRODUCT_TAGLINE,
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
    <html lang="en" data-scroll-behavior="smooth" className={`${geistSans.variable} ${geistMono.variable}`}>
      <body className="min-h-screen antialiased">
        <AppChrome user={user}>{children}</AppChrome>
      </body>
    </html>
  );
}
