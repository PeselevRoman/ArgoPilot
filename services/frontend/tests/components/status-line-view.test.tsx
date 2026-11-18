import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { StatusLineView } from "@/components/status-line-view";

const up = [
  { service: "registry-service", up: true },
  { service: "weather-service", up: true },
  { service: "planner-service", up: true },
] as const;

test("each service is named, with the word up or down (not colour alone)", () => {
  render(
    <StatusLineView
      statuses={[up[0], { service: "weather-service", up: false }, up[2]]}
    />,
  );
  expect(screen.getByText("Registry")).toBeInTheDocument();
  expect(screen.getByText("Weather")).toBeInTheDocument();
  expect(screen.getByText("Planner")).toBeInTheDocument();
  expect(screen.getAllByText("up")).toHaveLength(2);
  expect(screen.getAllByText("down")).toHaveLength(1);
});

test("while the check is running it says checking", () => {
  render(<StatusLineView statuses={null} />);
  expect(screen.getByText("Checking services")).toBeInTheDocument();
  expect(screen.queryByText("down")).not.toBeInTheDocument();
});

test("is a status region for assistive technology", () => {
  render(<StatusLineView statuses={[...up]} />);
  expect(screen.getByRole("status")).toBeInTheDocument();
});
