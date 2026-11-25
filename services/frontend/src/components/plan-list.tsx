import { StaleNotice } from "@/components/stale-notice";
import { dayLabel, formatNumber, plural } from "@/lib/format";
import type { PlanDay } from "@/lib/types";

function Value({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-base font-bold">{value}</dd>
    </div>
  );
}

// The days as a timeline: the content is a sequence of consecutive days. A filled blue marker is
// a day with irrigation, a hollow one a day without. Every number is the planner's, as given.
export function PlanList({ days }: { days: PlanDay[] }) {
  return (
    <ol className="border-l-2 border-border">
      {days.map((day, index) => {
        const water = day.runMinutes > 0;
        const { label, date } = dayLabel(day.date, index);
        return (
          <li key={day.date} className="relative py-4 pl-6">
            <span
              aria-hidden="true"
              className={
                water
                  ? "absolute top-5 -left-[9px] size-4 rounded-full bg-water"
                  : "absolute top-5 -left-[9px] size-4 rounded-full border-2 border-muted-foreground bg-background"
              }
            />
            <p className="flex flex-wrap items-baseline gap-x-3">
              <strong className="font-heading text-xl font-bold">{label}</strong>
              {index < 2 ? <time dateTime={day.date} className="text-sm text-muted-foreground">{date}</time> : null}
            </p>
            <p className="mt-1 text-xl font-bold">
              {water ? (
                <>
                  <span>{`${formatNumber(day.runMinutes)} ${plural(day.runMinutes, "minute", "minutes")}`}</span>
                  <span className="ml-3 text-base font-normal">{`${formatNumber(day.litres)} litres`}</span>
                </>
              ) : (
                <span className="text-muted-foreground">No irrigation</span>
              )}
            </p>
            <dl className="mt-2 grid grid-cols-3 gap-3">
              <Value label="Evaporation (ET0)" value={`${formatNumber(day.et0Mm)} mm`} />
              <Value label="Crop factor (Kc)" value={formatNumber(day.kc)} />
              <Value label="Soil water" value={`${formatNumber(day.bucketMm)} mm`} />
            </dl>
            {day.stale ? (
              <div className="mt-2">
                <StaleNotice compact />
              </div>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
