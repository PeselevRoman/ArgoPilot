import { describe, expect, test } from "vitest";
import { describeError } from "@/lib/messages";
import type { ServiceError } from "@/lib/types";

const err = (over: Partial<ServiceError>): ServiceError => ({
  service: "planner-service",
  kind: "problem",
  ...over,
});

describe("describeError", () => {
  test("an upstream failure names the service from the planner's detail", () => {
    const m = describeError(
      err({ status: 503, code: "UPSTREAM_UNAVAILABLE", detail: "weather-service is unavailable: ConnectError" }),
    );
    expect(m.title).toBe("The weather service is not available");
    expect(m.detail).toMatch(/plan/i);
  });

  test("an upstream failure that names the registry", () => {
    const m = describeError(
      err({ status: 503, code: "UPSTREAM_UNAVAILABLE", detail: "registry-service is unavailable: ReadTimeout" }),
    );
    expect(m.title).toBe("The registry is not available");
  });

  test("an upstream failure that names both services says either could be the cause", () => {
    const m = describeError(
      err({
        status: 503,
        code: "UPSTREAM_UNAVAILABLE",
        detail: "registry-service or weather-service returned a plan that is not valid",
      }),
    );
    expect(m.title).toBe("The registry or the weather service is not available");
  });

  test("an upstream failure that names no known service still says what happened", () => {
    const m = describeError(err({ status: 503, code: "UPSTREAM_UNAVAILABLE", detail: "something else" }));
    expect(m.title).toBe("A service the planner needs is not available");
  });

  test("a plot that does not exist", () => {
    expect(describeError(err({ status: 404, code: "NOT_FOUND" })).title).toBe("This plot does not exist");
    expect(describeError(err({ service: "registry-service", status: 404, code: "NOT_FOUND" })).title).toBe(
      "This plot does not exist",
    );
  });

  test.each([
    ["planner-service", "unreachable", "The planner is not available"],
    ["registry-service", "unreachable", "The registry is not available"],
    ["weather-service", "unreachable", "The weather service is not available"],
    ["planner-service", "timeout", "The planner took too long to answer"],
    ["registry-service", "timeout", "The registry took too long to answer"],
  ] as const)("%s, %s", (service, kind, title) => {
    expect(describeError({ service, kind }).title).toBe(title);
  });

  test("a bad answer says the app cannot use it", () => {
    const m = describeError({ service: "planner-service", kind: "bad-answer" });
    expect(m.title).toBe("The planner sent an answer this app cannot use");
  });

  test.each([
    [{ status: 503, code: "UNAVAILABLE" }],
    [{ status: 422, code: "VALIDATION" }],
    [{ status: 500 }],
    [{ status: 502, code: "SOMETHING_NEW" }],
  ])("any other problem %j is the generic message naming the planner", (over) => {
    expect(describeError(err(over)).title).toBe("The plan is not available right now");
  });

  test("the generic message names the registry when the registry failed", () => {
    const m = describeError(err({ service: "registry-service", status: 500 }));
    expect(m.title).toBe("The plan is not available right now");
    expect(m.detail).toMatch(/registry/i);
  });

  test("no message leaks a URL, a port, a status code, or a stack trace", () => {
    const hostile: ServiceError[] = [
      err({ status: 503, code: "UNAVAILABLE", detail: "Traceback at http://127.0.0.1:8002/x line 4" }),
      err({ status: 503, code: "UPSTREAM_UNAVAILABLE", detail: "http://127.0.0.1:8001 failed with 503" }),
      { service: "weather-service", kind: "unreachable" },
      { service: "planner-service", kind: "timeout" },
      { service: "planner-service", kind: "bad-answer" },
    ];
    for (const e of hostile) {
      const m = describeError(e);
      expect(`${m.title} ${m.detail}`).not.toMatch(/https?:|127\.|:\d{4}|\b[45]\d\d\b|Traceback|\bat \w+\.\w+/);
    }
  });
});
