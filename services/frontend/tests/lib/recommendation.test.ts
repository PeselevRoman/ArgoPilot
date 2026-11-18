import { describe, expect, test } from "vitest";
import { formatMinutes, todaysRecommendation } from "@/lib/recommendation";
import type { Plan, PlanDay } from "@/lib/types";

const day = (over: Partial<PlanDay> = {}): PlanDay => ({
  date: "2026-11-18",
  et0Mm: 2.76,
  kc: 0.8,
  litres: 0,
  runMinutes: 0,
  stale: false,
  bucketMm: 120.29,
  ...over,
});
const plan = (...days: PlanDay[]): Plan => ({ plotId: "p1", days });

describe("formatMinutes (display only: rounds up to whole minutes)", () => {
  test.each([
    [341.55, 342],
    [10, 10],
    [10.01, 11],
    [0.3, 1],
    [0, 0],
  ])("%d minutes is shown as %d", (input, expected) => {
    expect(formatMinutes(input)).toBe(expected);
  });
});

describe("todaysRecommendation", () => {
  test("water: whole minutes rounded up, and the litres as the planner gave them", () => {
    expect(todaysRecommendation(plan(day({ runMinutes: 341.55, litres: 18975 })))).toEqual({
      kind: "water",
      minutes: 342,
      litres: 18975,
      stale: false,
      date: "2026-11-18",
    });
  });

  test("no irrigation when run_minutes is 0", () => {
    expect(todaysRecommendation(plan(day()))).toEqual({ kind: "none", stale: false, date: "2026-11-18" });
  });

  // Review Focus 4: a small run is still a run.
  test("0.3 minutes is still water, for 1 minute", () => {
    expect(todaysRecommendation(plan(day({ runMinutes: 0.3, litres: 5 })))).toMatchObject({
      kind: "water",
      minutes: 1,
    });
  });

  test("the stale flag of today is carried, for both kinds", () => {
    expect(todaysRecommendation(plan(day({ stale: true })))).toMatchObject({ kind: "none", stale: true });
    expect(todaysRecommendation(plan(day({ stale: true, runMinutes: 20 })))).toMatchObject({
      kind: "water",
      stale: true,
    });
  });

  test("today is the first day of the plan, whatever the clock says, and later days do not matter", () => {
    const result = todaysRecommendation(
      plan(day({ date: "1999-01-01" }), day({ date: "1999-01-02", runMinutes: 50, litres: 1 })),
    );
    expect(result).toEqual({ kind: "none", stale: false, date: "1999-01-01" });
  });
});
