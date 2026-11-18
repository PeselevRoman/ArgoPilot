import Link from "next/link";
import { cropLabel } from "@/lib/format";
import type { FarmWithPlots } from "@/lib/types";

// Each farm is a heading and its plots are the list under it: that is the content's structure.
export function FarmList({ farms, unassignedPlots }: { farms: FarmWithPlots[]; unassignedPlots: number }) {
  if (farms.length === 0) {
    return <p className="text-base">No farms yet</p>;
  }
  return (
    <div className="space-y-8">
      {farms.map(({ farm, plots }) => (
        <section key={farm.id}>
          <h2 className="border-b border-border pb-2 font-heading text-2xl font-bold">{farm.name}</h2>
          {plots.length === 0 ? (
            <p className="py-3 text-muted-foreground">No plots yet</p>
          ) : (
            <ul>
              {plots.map((plot) => (
                <li key={plot.id} className="border-b border-border">
                  <Link href={`/plots/${encodeURIComponent(plot.id)}`} className="flex min-h-12 items-center justify-between gap-4 py-3">
                    <span className="text-lg font-bold">{plot.name}</span>
                    <span className="text-muted-foreground">{cropLabel(plot.cropId)}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </section>
      ))}
      {unassignedPlots > 0 ? (
        <p className="text-sm text-muted-foreground">
          {unassignedPlots} {unassignedPlots === 1 ? "plot is" : "plots are"} not shown because the farm it belongs to is not in the list.
        </p>
      ) : null}
    </div>
  );
}
