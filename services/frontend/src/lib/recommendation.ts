import type { Plan } from "@/lib/types";

export type Recommendation =
  | { kind: "water"; minutes: number; litres: number; stale: boolean; date: string }
  | { kind: "none"; stale: boolean; date: string };

// Display only: whole minutes, rounded up, so a run above 0 never reads as 0. The planner's
// number is not changed anywhere; this is how the headline is written.
export function formatMinutes(runMinutes: number): number {
  return Math.ceil(runMinutes);
}

// "Today" is the first day of the plan: the planner decides what today is for the plot's
// location. The server's own clock is never used.
export function todaysRecommendation(plan: Plan): Recommendation {
  const today = plan.days[0];
  if (today.runMinutes > 0) {
    return {
      kind: "water",
      minutes: formatMinutes(today.runMinutes),
      litres: today.litres,
      stale: today.stale,
      date: today.date,
    };
  }
  return { kind: "none", stale: today.stale, date: today.date };
}
