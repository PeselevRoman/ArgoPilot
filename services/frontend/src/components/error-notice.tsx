import type { ErrorMessage } from "@/lib/messages";

// What went wrong and what to do, in plain words. It replaces the plan: no numbers are shown.
// It has no button of its own: the way back is the link at the top of the plot page.
export function ErrorNotice({ message }: { message: ErrorMessage }) {
  return (
    <section role="alert" className="rounded-lg bg-fault-tint p-5 text-destructive">
      <h2 className="font-heading text-2xl font-bold">{message.title}</h2>
      <p className="mt-2 text-base">{message.detail}</p>
    </section>
  );
}
