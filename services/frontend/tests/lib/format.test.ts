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
])("formatNumber(%d) is %s", (value, text) => {
  expect(formatNumber(value)).toBe(text);
});

// The planner rounds to 2 decimals (3 for kc). Float noise such as 115.49000000000001 must not
// reach the screen, and no real decimal of the planner may be lost.
test("formatNumber keeps the planner's decimals (up to 3) and drops float noise", () => {
  expect(formatNumber(120.29)).toBe("120.29");
  expect(formatNumber(0.857)).toBe("0.857");
  expect(formatNumber(115.49000000000001)).toBe("115.49");
  expect(formatNumber(110.69000000000001)).toBe("110.69");
});

test("plural", () => {
  expect(plural(1, "minute", "minutes")).toBe("minute");
  expect(plural(0.3, "minute", "minutes")).toBe("minutes");
  expect(plural(2, "minute", "minutes")).toBe("minutes");
});
