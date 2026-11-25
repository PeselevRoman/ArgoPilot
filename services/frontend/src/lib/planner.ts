import { getConfig } from "@/lib/config";
import { getJson } from "@/lib/http";
import { parsePlan } from "@/lib/parse";
import type { Plan, Result } from "@/lib/types";

// The irrigation plan of one plot. An answer that is not a valid plan is "bad-answer", never
// a plan of zeros.
export async function getPlan(plotId: string, days = 7): Promise<Result<Plan>> {
  const url = `${getConfig().plannerUrl}/v1/plots/${encodeURIComponent(plotId)}/plan?days=${days}`;
  const result = await getJson("planner-service", url);
  if (!result.ok) return result;
  const plan = parsePlan(result.data);
  if (plan === null) return { ok: false, error: { service: "planner-service", kind: "bad-answer" } };
  return { ok: true, data: plan };
}
