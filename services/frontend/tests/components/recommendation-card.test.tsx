import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { RecommendationCard } from "@/components/recommendation-card";

test("water: the headline says the whole minutes, and the litres are shown", () => {
  render(
    <RecommendationCard
      recommendation={{ kind: "water", minutes: 342, litres: 18975, stale: false, date: "2026-11-18" }}
    />,
  );
  expect(screen.getByRole("heading", { name: "Water for 342 minutes" })).toBeInTheDocument();
  expect(screen.getByText(/18[\s,  ]?975 litres/)).toBeInTheDocument();
});

test("one minute is singular", () => {
  render(<RecommendationCard recommendation={{ kind: "water", minutes: 1, litres: 5, stale: false, date: "2026-11-18" }} />);
  expect(screen.getByRole("heading", { name: "Water for 1 minute" })).toBeInTheDocument();
});

test("none: the headline says there is no irrigation today", () => {
  render(<RecommendationCard recommendation={{ kind: "none", stale: false, date: "2026-11-18" }} />);
  expect(screen.getByRole("heading", { name: "No irrigation today" })).toBeInTheDocument();
});

test("a stale forecast shows a notice that says so, for both kinds", () => {
  const { rerender } = render(
    <RecommendationCard recommendation={{ kind: "water", minutes: 20, litres: 100, stale: true, date: "2026-11-18" }} />,
  );
  expect(screen.getByText("Old forecast")).toBeInTheDocument();
  rerender(<RecommendationCard recommendation={{ kind: "none", stale: true, date: "2026-11-18" }} />);
  expect(screen.getByText("Old forecast")).toBeInTheDocument();
});

test("a fresh forecast shows no stale notice", () => {
  render(<RecommendationCard recommendation={{ kind: "none", stale: false, date: "2026-11-18" }} />);
  expect(screen.queryByText("Old forecast")).not.toBeInTheDocument();
});
