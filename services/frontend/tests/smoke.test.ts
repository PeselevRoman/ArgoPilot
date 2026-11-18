import { expect, test } from "vitest";
import { APP_NAME } from "@/lib/version";

test("the app is called AgroPilot", () => {
  expect(APP_NAME).toBe("AgroPilot");
});
