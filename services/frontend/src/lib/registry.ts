import { getConfig } from "@/lib/config";
import { getJson } from "@/lib/http";
import { parseFarms, parsePlot, parsePlots } from "@/lib/parse";
import type { FarmWithPlots, Plot, Result } from "@/lib/types";

const badAnswer = { ok: false, error: { service: "registry-service", kind: "bad-answer" } } as const;

export type FarmsWithPlots = {
  farms: FarmWithPlots[];
  // Plots whose farm is not in the farm list. They are shown under no farm, but counted.
  unassignedPlots: number;
};

export async function listFarmsWithPlots(): Promise<Result<FarmsWithPlots>> {
  const base = getConfig().registryUrl;
  // Promise.all is like Task.WhenAll in C#: both calls run at the same time.
  const [farmsResult, plotsResult] = await Promise.all([
    getJson("registry-service", `${base}/v1/farms`),
    getJson("registry-service", `${base}/v1/plots`),
  ]);
  if (!farmsResult.ok) return farmsResult;
  if (!plotsResult.ok) return plotsResult;

  const farms = parseFarms(farmsResult.data);
  const plots = parsePlots(plotsResult.data);
  if (farms === null || plots === null) return badAnswer;

  const byFarm = new Map<string, Plot[]>(farms.map((farm) => [farm.id, []]));
  let unassignedPlots = 0;
  for (const plot of plots) {
    const list = byFarm.get(plot.farmId);
    if (list) list.push(plot);
    else unassignedPlots += 1;
  }
  return {
    ok: true,
    data: { farms: farms.map((farm) => ({ farm, plots: byFarm.get(farm.id) ?? [] })), unassignedPlots },
  };
}

export async function getPlot(id: string): Promise<Result<Plot>> {
  const result = await getJson("registry-service", `${getConfig().registryUrl}/v1/plots/${encodeURIComponent(id)}`);
  if (!result.ok) return result;
  const plot = parsePlot(result.data);
  return plot === null ? badAnswer : { ok: true, data: plot };
}
