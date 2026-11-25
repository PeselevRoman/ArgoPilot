import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { checkHealth } from "@/lib/health";

function reply(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

beforeEach(() => {
  vi.stubEnv("REGISTRY_URL", "http://registry");
  vi.stubEnv("WEATHER_URL", "http://weather");
  vi.stubEnv("PLANNER_URL", "http://planner");
  vi.stubEnv("REQUEST_TIMEOUT_MS", "50");
});
afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

// A fake fetch that answers by host.
function stubHosts(byHost: Record<string, () => Promise<Response> | Response>) {
  const fake = vi.fn(async (url: string) => byHost[new URL(url).host]());
  vi.stubGlobal("fetch", fake);
  return fake;
}

const ok = () => reply({ status: "ok" });

test("all three up: three entries in a fixed order, each asked at /health", async () => {
  const fake = stubHosts({ registry: ok, weather: ok, planner: ok });
  expect(await checkHealth()).toEqual([
    { service: "registry-service", up: true },
    { service: "weather-service", up: true },
    { service: "planner-service", up: true },
  ]);
  expect(fake.mock.calls.map((c) => c[0]).sort()).toEqual([
    "http://planner/health",
    "http://registry/health",
    "http://weather/health",
  ]);
});

test("one unreachable service is down and the others are unaffected", async () => {
  stubHosts({
    registry: ok,
    weather: () => {
      throw new TypeError("fetch failed");
    },
    planner: ok,
  });
  const result = await checkHealth();
  expect(result.map((s) => s.up)).toEqual([true, false, true]);
});

test("a service that answers 503 is down", async () => {
  stubHosts({ registry: () => reply({ code: "UNAVAILABLE" }, 503), weather: ok, planner: ok });
  expect((await checkHealth())[0]).toEqual({ service: "registry-service", up: false });
});

// Review Focus 3: a 200 is not enough; the body must say ok.
test.each([
  ["status is not ok", () => reply({ status: "degraded" })],
  ["the body is not JSON", () => new Response("OK", { status: 200 })],
  ["the body is an empty object", () => reply({})],
])("a 200 where %s is down", async (_name, answer) => {
  stubHosts({ registry: ok, weather: ok, planner: answer });
  expect((await checkHealth())[2]).toEqual({ service: "planner-service", up: false });
});

test("a service that does not answer in time is down, and the three checks run at the same time", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init: RequestInit) =>
      new Promise<Response>((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
      }),
    ),
  );
  const started = Date.now();
  const result = await checkHealth();
  expect(result.map((s) => s.up)).toEqual([false, false, false]);
  // Three sequential 50 ms timeouts would take 150 ms or more.
  expect(Date.now() - started).toBeLessThan(140);
});
