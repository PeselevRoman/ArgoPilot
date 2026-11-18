import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { ErrorNotice } from "@/components/error-notice";

const message = { title: "The weather service is not available", detail: "Try again in a few minutes." };

test("shows the title and the detail", () => {
  render(<ErrorNotice message={message} />);
  expect(screen.getByRole("heading", { name: message.title })).toBeInTheDocument();
  expect(screen.getByText(message.detail)).toBeInTheDocument();
});

test("is announced to assistive technology", () => {
  render(<ErrorNotice message={message} />);
  expect(screen.getByRole("alert")).toBeInTheDocument();
});

test("shows a link back when backHref is set, and none otherwise", () => {
  const { rerender } = render(<ErrorNotice message={message} backHref="/" />);
  expect(screen.getByRole("link", { name: "Back to all plots" })).toHaveAttribute("href", "/");
  rerender(<ErrorNotice message={message} />);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
});
