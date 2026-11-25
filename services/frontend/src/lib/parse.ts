import type { Farm, Plan, PlanDay, Plot } from "@/lib/types";

// Strict parsers for the services' JSON. Each returns the typed value, or null when the answer
// does not have the expected shape. Nothing is repaired or defaulted: an answer we cannot trust
// is treated as the service being unavailable (see the callers).

type Obj = Record<string, unknown>;

function isObj(x: unknown): x is Obj {
  return typeof x === "object" && x !== null && !Array.isArray(x);
}

const isText = (x: unknown): x is string => typeof x === "string";
// Number.isFinite is false for NaN and Infinity, and for anything that is not a number.
const isNum = (x: unknown): x is number => typeof x === "number" && Number.isFinite(x);
// A plan has no negative water, minutes, evaporation or crop factor: a negative value is a sign
// the answer cannot be trusted, so it is refused, not shown.
const isNonNegative = (x: unknown): x is number => isNum(x) && x >= 0;

function parseList<T>(x: unknown, parseItem: (item: unknown) => T | null): T[] | null {
  if (!Array.isArray(x)) return null;
  const items: T[] = [];
  for (const raw of x) {
    const item = parseItem(raw);
    if (item === null) return null;
    items.push(item);
  }
  return items;
}

function parseFarm(x: unknown): Farm | null {
  if (!isObj(x) || !isText(x.id) || !isText(x.name)) return null;
  return { id: x.id, name: x.name };
}

export function parsePlot(x: unknown): Plot | null {
  if (!isObj(x) || !isText(x.id) || !isText(x.farm_id) || !isText(x.name)) return null;
  if (!isText(x.crop_id) || !isNum(x.area_m2) || x.area_m2 <= 0) return null;
  return { id: x.id, farmId: x.farm_id, name: x.name, cropId: x.crop_id, areaM2: x.area_m2 };
}

function parsePlanDay(x: unknown): PlanDay | null {
  if (!isObj(x)) return null;
  if (!isText(x.date) || !/^\d{4}-\d{2}-\d{2}$/.test(x.date)) return null;
  if (!isNonNegative(x.et0_mm) || !isNonNegative(x.kc) || !isNonNegative(x.litres)) return null;
  if (!isNonNegative(x.run_minutes) || !isNonNegative(x.bucket_mm) || typeof x.stale !== "boolean") return null;
  return {
    date: x.date,
    et0Mm: x.et0_mm,
    kc: x.kc,
    litres: x.litres,
    runMinutes: x.run_minutes,
    stale: x.stale,
    bucketMm: x.bucket_mm,
  };
}

export const parseFarms = (x: unknown): Farm[] | null => parseList(x, parseFarm);
export const parsePlots = (x: unknown): Plot[] | null => parseList(x, parsePlot);

export function parsePlan(x: unknown): Plan | null {
  if (!isObj(x) || !isText(x.plot_id)) return null;
  const days = parseList(x.days, parsePlanDay);
  // An empty plan is refused: it would read as "no irrigation needed".
  if (days === null || days.length === 0) return null;
  return { plotId: x.plot_id, days };
}
