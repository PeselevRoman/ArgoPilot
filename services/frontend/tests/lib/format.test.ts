import { describe, expect, test } from "vitest";
import { cropLabel, dayLabel, formatNumber, plural } from "@/lib/format";

test.each([
  ["tomato", "Tomato"],
  ["bell-pepper", "Bell pepper"],
])("cropLabel(%s) is %s", (id, label) => {
  expect(cropLabel(id)).toBe(label);
});

describe("dayLabel", () => {
  test("the first two days are Today and Tomorrow, and keep their date", () => {
    expect(dayLabel("2026-11-20", 0)).toEqual({ label: "Today", date: "Fri 20 Nov" });
    expect(dayLabel("2026-11-21", 1)).toEqual({ label: "Tomorrow", date: "Sat 21 Nov" });
  });
  test("later days are labelled by their date", () => {
    expect(dayLabel("2026-11-22", 2).label).toBe("Sun 22 Nov");
  });
  test("the date text never moves to another day, whatever the machine's timezone", () => {
    expect(dayLabel("2026-01-01", 5).label).toBe("Thu 1 Jan");
    expect(dayLabel("2026-12-31", 5).label).toBe("Thu 31 Dec");
  });
});

test.each([
  [18975, "18,975"],
  [341.55, "341.55"],
  [0, "0"],
  [0.8, "0.8"],
])("formatNumber(%d) is %s and never rounds", (value, text) => {
  expect(formatNumber(value)).toBe(text);
});

test("formatNumber keeps every decimal the planner gave", () => {
  expect(formatNumber(120.29)).toBe("120.29");
  expect(formatNumber(0.123456)).toBe("0.123456");
});

test("plural", () => {
  expect(plural(1, "minute", "minutes")).toBe("minute");
  expect(plural(0.3, "minute", "minutes")).toBe("minutes");
  expect(plural(2, "minute", "minutes")).toBe("minutes");
});
