import type { Metadata } from "next";
import { Atkinson_Hyperlegible_Next, Bricolage_Grotesque } from "next/font/google";
import { Suspense } from "react";
import { StatusLine } from "@/components/status-line";
import { StatusLineView } from "@/components/status-line-view";
import "./globals.css";

// Two fonts, as in docs/superpowers/specs/2026-11-18-frontend-visual-design.md.
const display = Bricolage_Grotesque({ variable: "--font-display", subsets: ["latin"] });
const body = Atkinson_Hyperlegible_Next({ variable: "--font-body", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "AgroPilot",
  description: "Should I water this plot today, and for how many minutes?",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${display.variable} ${body.variable}`}>
      <body className="min-h-dvh">
        <div className="mx-auto w-full max-w-[40rem] px-4 pb-16">
          <header className="flex flex-wrap items-baseline justify-between gap-x-6 gap-y-1 border-b border-border py-3">
            <span className="font-heading text-lg font-extrabold">AgroPilot</span>
            <Suspense fallback={<StatusLineView statuses={null} />}>
              <StatusLine />
            </Suspense>
          </header>
          <main className="pt-6">{children}</main>
        </div>
      </body>
    </html>
  );
}
