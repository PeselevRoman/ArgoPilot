import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { getPlan } from "@/lib/planner";

const day = { date: "2026-11-18", et0_mm: 2.76, kc: 0.8, litres: 0, run_minutes: 0, stale: false, bucket_mm: 120.29 };

function reply(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

beforeEach(() => {
  vi.stubEnv("REGISTRY_URL", "http://registry");
  vi.stubEnv("WEATHER_URL", "http://weather");
  vi.stubEnv("PLANNER_URL", "http://planner");
  vi.stubEnv("REQUEST_TIMEOUT_MS", "1000");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

test("asks the planner for 7 days by default and returns the parsed plan", async () => {
  const fake = vi.fn().mockResolvedValue(reply({ plot_id: "p1", days: [day] }));
  vi.stubGlobal("fetch", fake);
  const result = await getPlan("p1");
  expect(fake.mock.calls[0][0]).toBe("http://planner/v1/plots/p1/plan?days=7");
  expect(result).toMatchObject({ ok: true, data: { plotId: "p1", days: [{ date: "2026-11-18", runMinutes: 0 }] } });
});

test("an invalid plan is a bad-answer from planner-service", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({ plot_id: "p1", days: [{ date: "2026-11-18" }] })));
  expect(await getPlan("p1")).toEqual({ ok: false, error: { service: "planner-service", kind: "bad-answer" } });
});

// Review Focus 1: an empty plan must never read as "No irrigation today".
test("a plan with no days is a bad-answer", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(reply({ plot_id: "p1", days: [] })));
  expect(await getPlan("p1")).toEqual({ ok: false, error: { service: "planner-service", kind: "bad-answer" } });
});

test("a problem answer passes through", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(reply({ code: "UPSTREAM_UNAVAILABLE", detail: "weather-service is unavailable" }, 503)),
  );
  expect(await getPlan("p1")).toEqual({
    ok: false,
    error: {
      service: "planner-service",
      kind: "problem",
      status: 503,
      code: "UPSTREAM_UNAVAILABLE",
      detail: "weather-service is unavailable",
    },
  });
});

// Review Focus 2: a plot id must not be able to change the path.
test("the plot id is encoded into the URL", async () => {
  const fake = vi.fn().mockResolvedValue(reply({ plot_id: "x", days: [day] }));
  vi.stubGlobal("fetch", fake);
  await getPlan("../health");
  expect(fake.mock.calls[0][0]).toBe("http://planner/v1/plots/..%2Fhealth/plan?days=7");
});
