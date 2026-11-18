import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { getJson } from "@/lib/http";

function jsonResponse(body: unknown, init: ResponseInit = {}, type = "application/json") {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": type },
    ...init,
  });
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

test("a 200 JSON body is returned as data", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(jsonResponse({ hello: "world" })));
  expect(await getJson("registry-service", "http://registry/x")).toEqual({
    ok: true,
    data: { hello: "world" },
  });
});

test("the call asks for no caching", async () => {
  const fake = vi.fn().mockResolvedValue(jsonResponse({}));
  vi.stubGlobal("fetch", fake);
  await getJson("registry-service", "http://registry/x");
  expect(fake.mock.calls[0][0]).toBe("http://registry/x");
  expect(fake.mock.calls[0][1]).toMatchObject({ cache: "no-store" });
});

test("a network error is kind unreachable", async () => {
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));
  expect(await getJson("planner-service", "http://planner/x")).toEqual({
    ok: false,
    error: { service: "planner-service", kind: "unreachable" },
  });
});

test("a call that takes longer than the timeout is kind timeout", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn((_url: string, init: RequestInit) =>
      new Promise((_resolve, reject) => {
        init.signal?.addEventListener("abort", () => reject(init.signal?.reason));
      }),
    ),
  );
  const result = await getJson("weather-service", "http://weather/health");
  expect(result).toEqual({ ok: false, error: { service: "weather-service", kind: "timeout" } });
});

test("a problem+json answer keeps its status, code and detail", async () => {
  const body = { code: "UPSTREAM_UNAVAILABLE", detail: "weather-service is unavailable: ConnectError" };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(jsonResponse(body, { status: 503 }, "application/problem+json")),
  );
  expect(await getJson("planner-service", "http://planner/x")).toEqual({
    ok: false,
    error: { service: "planner-service", kind: "problem", status: 503, ...body },
  });
});

test("a 404 problem answer is kind problem with status 404", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      jsonResponse({ code: "NOT_FOUND", detail: "Plot not found" }, { status: 404 }, "application/problem+json"),
    ),
  );
  const result = await getJson("planner-service", "http://planner/x");
  expect(result).toMatchObject({ ok: false, error: { kind: "problem", status: 404, code: "NOT_FOUND" } });
});

test("an error status with a body that is not JSON is kind problem, without code or detail", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("Bad gateway", { status: 502 })));
  expect(await getJson("registry-service", "http://registry/x")).toEqual({
    ok: false,
    error: { service: "registry-service", kind: "problem", status: 502 },
  });
});

test("a detail that is not a string is dropped", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(jsonResponse({ code: 5, detail: { a: 1 } }, { status: 503 })),
  );
  expect(await getJson("registry-service", "http://registry/x")).toEqual({
    ok: false,
    error: { service: "registry-service", kind: "problem", status: 503 },
  });
});

test("a 200 whose body is not JSON is kind bad-answer", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response("<html>", { status: 200 })));
  expect(await getJson("registry-service", "http://registry/x")).toEqual({
    ok: false,
    error: { service: "registry-service", kind: "bad-answer" },
  });
});
