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

// The way back is the "Back to all plots" link at the top of the plot page, so the notice has no
// second button: one place, one name.
test("has no link or button of its own", () => {
  render(<ErrorNotice message={message} />);
  expect(screen.queryByRole("link")).not.toBeInTheDocument();
  expect(screen.queryByRole("button")).not.toBeInTheDocument();
});
