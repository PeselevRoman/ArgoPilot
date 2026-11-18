"use client";

import { Button } from "@/components/ui/button";

// Next.js shows this when something unexpected breaks while a page is drawn. It shows no message
// or stack from the exception: the grower gets a sentence and a way to try again.
export default function ErrorPage({ reset }: { error: Error; reset: () => void }) {
  return (
    <section role="alert" className="rounded-lg bg-fault-tint p-5 text-destructive">
      <h1 className="font-heading text-2xl font-bold">This page could not be shown</h1>
      <p className="mt-2 text-base">Something went wrong while drawing it. Try again in a few minutes.</p>
      <Button variant="outline" className="mt-4 h-12 px-4 text-base text-foreground" onClick={reset}>
        Try again
      </Button>
    </section>
  );
}
