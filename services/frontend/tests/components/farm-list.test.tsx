import { render, screen, within } from "@testing-library/react";
import { expect, test } from "vitest";
import { FarmList } from "@/components/farm-list";
import type { FarmWithPlots } from "@/lib/types";

const plot = (id: string, name: string, cropId = "tomato") => ({
  id,
  farmId: "f1",
  name,
  cropId,
  areaM2: 1000,
});
const farms: FarmWithPlots[] = [
  { farm: { id: "f1", name: "North farm" }, plots: [plot("p1", "North block"), plot("p2", "East block", "bell-pepper")] },
  { farm: { id: "f2", name: "South farm" }, plots: [] },
];

test("each farm is a heading and each plot a link to its page", () => {
  render(<FarmList farms={farms} unassignedPlots={0} />);
  expect(screen.getByRole("heading", { name: "North farm" })).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /North block/ })).toHaveAttribute("href", "/plots/p1");
  expect(screen.getByRole("link", { name: /East block/ })).toHaveAttribute("href", "/plots/p2");
});

test("the crop is shown in words, not as an id", () => {
  render(<FarmList farms={farms} unassignedPlots={0} />);
  expect(within(screen.getByRole("link", { name: /East block/ })).getByText("Bell pepper")).toBeInTheDocument();
});

test("a farm without plots says so", () => {
  render(<FarmList farms={farms} unassignedPlots={0} />);
  expect(screen.getByText("No plots yet")).toBeInTheDocument();
});

test("no farms at all says so", () => {
  render(<FarmList farms={[]} unassignedPlots={0} />);
  expect(screen.getByText("No farms yet")).toBeInTheDocument();
});

test("plots that belong to no listed farm are counted in a note", () => {
  render(<FarmList farms={farms} unassignedPlots={2} />);
  expect(screen.getByText(/2 plots are not shown/)).toBeInTheDocument();
});

test("no note when every plot has a farm", () => {
  render(<FarmList farms={farms} unassignedPlots={0} />);
  expect(screen.queryByText(/not shown/)).not.toBeInTheDocument();
});
