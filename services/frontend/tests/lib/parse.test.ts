import { describe, expect, test } from "vitest";
import { parseFarms, parsePlan, parsePlot, parsePlots } from "@/lib/parse";

const day = {
  date: "2026-11-18",
  et0_mm: 2.76,
  kc: 0.8,
  litres: 0,
  run_minutes: 0,
  stale: false,
  bucket_mm: 120.29,
};
const plan = { plot_id: "p1", days: [day, { ...day, date: "2026-11-19" }] };

describe("parsePlan", () => {
  test("converts a valid plan to camelCase", () => {
    expect(parsePlan(plan)).toEqual({
      plotId: "p1",
      days: [
        { date: "2026-11-18", et0Mm: 2.76, kc: 0.8, litres: 0, runMinutes: 0, stale: false, bucketMm: 120.29 },
        { date: "2026-11-19", et0Mm: 2.76, kc: 0.8, litres: 0, runMinutes: 0, stale: false, bucketMm: 120.29 },
      ],
    });
  });

  test("ignores fields the frontend does not use", () => {
    expect(parsePlan({ ...plan, extra: 1, days: [{ ...day, extra: 2 }] })).not.toBeNull();
  });

  test.each([
    ["days empty", { ...plan, days: [] }],
    ["days missing", { plot_id: "p1" }],
    ["plot_id missing", { days: [day] }],
    ["not an object", "plan"],
    ["null", null],
    ["a day is not an object", { ...plan, days: [5] }],
    ["stale is not a boolean", { ...plan, days: [{ ...day, stale: "no" }] }],
    ["date is not YYYY-MM-DD", { ...plan, days: [{ ...day, date: "18/11/2026" }] }],
    ["a number is text", { ...plan, days: [{ ...day, litres: "6900" }] }],
    ["a number is null", { ...plan, days: [{ ...day, kc: null }] }],
    ["a number is NaN", { ...plan, days: [{ ...day, et0_mm: NaN }] }],
    ["a number is Infinity", { ...plan, days: [{ ...day, run_minutes: Infinity }] }],
  ])("returns null when %s", (_name, input) => {
    expect(parsePlan(input)).toBeNull();
  });

  test.each(["et0_mm", "kc", "litres", "run_minutes", "stale", "bucket_mm", "date"])(
    "returns null when a day has no %s",
    (field) => {
      const broken: Record<string, unknown> = { ...day };
      delete broken[field];
      expect(parsePlan({ ...plan, days: [broken] })).toBeNull();
    },
  );
});

describe("parseFarms", () => {
  test("converts a list of farms", () => {
    expect(parseFarms([{ id: "f1", name: "North" }])).toEqual([{ id: "f1", name: "North" }]);
  });
  test("an empty list is valid", () => {
    expect(parseFarms([])).toEqual([]);
  });
  test.each([
    ["not an array", { id: "f1" }],
    ["a farm without an id", [{ name: "North" }]],
    ["a farm with a number as name", [{ id: "f1", name: 5 }]],
  ])("returns null for %s", (_name, input) => {
    expect(parseFarms(input)).toBeNull();
  });
});

describe("parsePlots / parsePlot", () => {
  const plot = { id: "p1", farm_id: "f1", name: "North block", crop_id: "tomato", area_m2: 1000 };
  const parsed = { id: "p1", farmId: "f1", name: "North block", cropId: "tomato", areaM2: 1000 };

  test("convert snake_case to camelCase", () => {
    expect(parsePlots([plot])).toEqual([parsed]);
    expect(parsePlot(plot)).toEqual(parsed);
  });
  test.each(["id", "farm_id", "name", "crop_id", "area_m2"])("return null when %s is missing", (field) => {
    const broken: Record<string, unknown> = { ...plot };
    delete broken[field];
    expect(parsePlot(broken)).toBeNull();
    expect(parsePlots([broken])).toBeNull();
  });
  test("return null for a non-finite area", () => {
    expect(parsePlot({ ...plot, area_m2: Infinity })).toBeNull();
  });
  test("parsePlots returns null when it is not an array", () => {
    expect(parsePlots(plot)).toBeNull();
  });
});
