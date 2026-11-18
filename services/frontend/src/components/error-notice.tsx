import Link from "next/link";
import { buttonVariants } from "@/components/ui/button";
import type { ErrorMessage } from "@/lib/messages";

// What went wrong and what to do, in plain words. It replaces the plan: no numbers are shown.
export function ErrorNotice({ message, backHref }: { message: ErrorMessage; backHref?: string }) {
  return (
    <section role="alert" className="rounded-lg bg-fault-tint p-5 text-destructive">
      <h2 className="font-heading text-2xl font-bold">{message.title}</h2>
      <p className="mt-2 text-base">{message.detail}</p>
      {backHref ? (
        <Link
          href={backHref}
          className={`${buttonVariants({ variant: "outline" })} mt-4 h-12 px-4 text-base text-foreground`}
        >
          Back to all plots
        </Link>
      ) : null}
    </section>
  );
}
