import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { PlanList } from "@/components/plan-list";
import type { PlanDay } from "@/lib/types";

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

test("one list item per day, in order, with Today and Tomorrow for the first two", () => {
  render(
    <PlanList
      days={[day(), day({ date: "2026-11-19" }), day({ date: "2026-11-20" })]}
    />,
  );
  const items = screen.getAllByRole("listitem");
  expect(items).toHaveLength(3);
  expect(within(items[0]).getByText("Today")).toBeInTheDocument();
  expect(within(items[1]).getByText("Tomorrow")).toBeInTheDocument();
  expect(within(items[2]).getByText(/Fri/)).toBeInTheDocument();
  expect(within(items[2]).getByText(/20 Nov/)).toBeInTheDocument();
});

test("a day without irrigation says so", () => {
  render(<PlanList days={[day()]} />);
  expect(screen.getByText("No irrigation")).toBeInTheDocument();
});

test("an irrigation day shows the planner's minutes and litres, unchanged", () => {
  render(<PlanList days={[day({ runMinutes: 341.55, litres: 18975 })]} />);
  const item = screen.getByRole("listitem");
  expect(within(item).getByText("341.55 minutes")).toBeInTheDocument();
  expect(within(item).getByText(/18[\s,  ]?975 litres/)).toBeInTheDocument();
});

test("every day shows et0, kc and the soil water level as the planner gave them", () => {
  render(<PlanList days={[day({ et0Mm: 3.07, kc: 0.8, bucketMm: 117.84 })]} />);
  const item = screen.getByRole("listitem");
  expect(within(item).getByText("3.07 mm")).toBeInTheDocument();
  expect(within(item).getByText("0.8")).toBeInTheDocument();
  expect(within(item).getByText("117.84 mm")).toBeInTheDocument();
});

test("only the stale day has the stale marker", () => {
  render(<PlanList days={[day(), day({ date: "2026-11-19", stale: true })]} />);
  const items = screen.getAllByRole("listitem");
  expect(within(items[0]).queryByText("Old forecast")).not.toBeInTheDocument();
  expect(within(items[1]).getByText("Old forecast")).toBeInTheDocument();
});
