import Link from "next/link";
import { Chevron } from "@/components/chevron";

// The way back to the list of plots, at the top of the plot page. Underlined and with a chevron:
// a link you can see is a link without hovering (a phone has no hover).
export function BackLink() {
  return (
    <Link href="/" className="-ml-1 mb-2 inline-flex min-h-12 items-center gap-1 pr-3 font-bold underline underline-offset-4 decoration-2">
      <Chevron direction="left" />
      Back to all plots
    </Link>
  );
}
