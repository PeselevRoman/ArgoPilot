import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { BackLink } from "@/components/back-link";

test("is a link to the home page with the words 'Back to all plots'", () => {
  render(<BackLink />);
  expect(screen.getByRole("link", { name: "Back to all plots" })).toHaveAttribute("href", "/");
});

test("has an icon that screen readers skip, and is underlined so it reads as a link", () => {
  render(<BackLink />);
  const link = screen.getByRole("link", { name: "Back to all plots" });
  expect(link.querySelector("svg")).toHaveAttribute("aria-hidden", "true");
  expect(link.className).toMatch(/underline/);
});
