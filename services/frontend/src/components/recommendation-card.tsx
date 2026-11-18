import { StaleNotice } from "@/components/stale-notice";
import { formatNumber, plural } from "@/lib/format";
import type { Recommendation } from "@/lib/recommendation";

// Today's answer, the one big thing on the plot page. When the plot needs water the whole slab is
// solid water-blue, when not it is a plain outlined panel: readable before a word is read.
export function RecommendationCard({ recommendation }: { recommendation: Recommendation }) {
  const water = recommendation.kind === "water";
  return (
    <section
      className={
        water
          ? "rounded-lg bg-primary p-5 text-primary-foreground"
          : "rounded-lg border-2 border-muted-foreground/40 p-5"
      }
    >
      <h2 className="font-heading text-[clamp(2.5rem,12vw,4.5rem)] leading-[1.02] font-extrabold tracking-tight">
        {recommendation.kind === "water"
          ? `Water for ${recommendation.minutes} ${plural(recommendation.minutes, "minute", "minutes")}`
          : "No irrigation today"}
      </h2>
      <p className="mt-3 text-base">
        {recommendation.kind === "water"
          ? `${formatNumber(recommendation.litres)} litres, today`
          : "The soil has enough water today."}
      </p>
      {recommendation.stale ? (
        <div className="mt-4">
          <StaleNotice />
        </div>
      ) : null}
    </section>
  );
}
