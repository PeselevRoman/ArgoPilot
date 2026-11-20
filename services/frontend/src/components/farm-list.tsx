import Link from "next/link";
import { Chevron } from "@/components/chevron";
import { cropLabel } from "@/lib/format";
import type { FarmWithPlots } from "@/lib/types";

// Each farm is a heading and its plots are the list under it: that is the content's structure.
export function FarmList({ farms, unassignedPlots }: { farms: FarmWithPlots[]; unassignedPlots: number }) {
  const note =
    unassignedPlots > 0 ? (
      <p className="text-sm text-muted-foreground">
        {unassignedPlots === 1
          ? "1 plot is not shown because its farm is not in the list."
          : `${unassignedPlots} plots are not shown because their farm is not in the list.`}
      </p>
    ) : null;
  if (farms.length === 0) {
    return (
      <div className="space-y-4">
        <p className="text-base">No farms yet</p>
        {note}
      </div>
    );
  }
  return (
    <div className="space-y-8">
      {farms.map(({ farm, plots }) => (
        <section key={farm.id}>
          <h2 className="font-heading text-2xl font-bold">{farm.name}</h2>
          {plots.length === 0 ? (
            <p className="py-3 text-muted-foreground">No plots yet</p>
          ) : (
            // One outlined, white group per farm. The border, the chevron and the pressed colour
            // say "you can press these"; the farm name above is flat text.
            <ul className="mt-3 overflow-hidden rounded-lg border-[1.5px] border-foreground bg-card">
              {plots.map((plot) => (
                <li key={plot.id} className="border-b border-border last:border-b-0">
                  <Link
                    href={`/plots/${encodeURIComponent(plot.id)}`}
                    className="flex min-h-14 items-center justify-between gap-3 px-4 py-3 hover:bg-pressed active:bg-pressed"
                  >
                    <span className="text-lg font-bold">{plot.name}</span>
                    <span className="flex items-center gap-1 text-muted-foreground">
                      {cropLabel(plot.cropId)}
                      <Chevron className="text-foreground" />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
      {note}
    </div>
  );
}
