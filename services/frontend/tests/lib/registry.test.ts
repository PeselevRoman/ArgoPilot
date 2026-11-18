import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { getPlot, listFarmsWithPlots } from "@/lib/registry";

const plot = (id: string, farmId: string) => ({
  id,
  farm_id: farmId,
  name: `Plot ${id}`,
  crop_id: "tomato",
  area_m2: 1000,
});

function reply(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
}

// A fake fetch that answers by URL path.
function stubRegistry(routes: Record<string, () => Response>) {
  const fake = vi.fn(async (url: string) => {
    const path = new URL(url).pathname;
    const route = routes[path];
    if (!route) throw new Error(`unexpected call ${url}`);
    return route();
  });
  vi.stubGlobal("fetch", fake);
  return fake;
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

test("groups plots under their farm and keeps the registry's order", async () => {
  stubRegistry({
    "/v1/farms": () =>
      reply([
        { id: "f1", name: "North" },
        { id: "f2", name: "South" },
      ]),
    "/v1/plots": () => reply([plot("a", "f2"), plot("b", "f1"), plot("c", "f1")]),
  });
  const result = await listFarmsWithPlots();
  expect(result).toMatchObject({ ok: true });
  if (!result.ok) return;
  expect(result.data.farms.map((f) => [f.farm.name, f.plots.map((p) => p.id)])).toEqual([
    ["North", ["b", "c"]],
    ["South", ["a"]],
  ]);
  expect(result.data.unassignedPlots).toBe(0);
});

test("a farm with no plots has an empty list", async () => {
  stubRegistry({ "/v1/farms": () => reply([{ id: "f1", name: "North" }]), "/v1/plots": () => reply([]) });
  const result = await listFarmsWithPlots();
  expect(result).toMatchObject({ ok: true, data: { farms: [{ farm: { id: "f1" }, plots: [] }] } });
});

// Review Focus 5: a plot whose farm does not exist must not crash the page, nor vanish unnoticed.
test("a plot with an unknown farm is counted, and shown under no farm", async () => {
  stubRegistry({
    "/v1/farms": () => reply([{ id: "f1", name: "North" }]),
    "/v1/plots": () => reply([plot("a", "f1"), plot("b", "ghost")]),
  });
  const result = await listFarmsWithPlots();
  if (!result.ok) throw new Error("expected ok");
  expect(result.data.unassignedPlots).toBe(1);
  expect(result.data.farms[0].plots.map((p) => p.id)).toEqual(["a"]);
});

test("if one of the two calls fails, the result is that registry error", async () => {
  stubRegistry({ "/v1/farms": () => reply([]), "/v1/plots": () => reply({ code: "UNAVAILABLE" }, 503) });
  expect(await listFarmsWithPlots()).toMatchObject({
    ok: false,
    error: { service: "registry-service", kind: "problem", status: 503 },
  });
});

test("an invalid farm list is a bad-answer", async () => {
  stubRegistry({ "/v1/farms": () => reply({ oops: true }), "/v1/plots": () => reply([]) });
  expect(await listFarmsWithPlots()).toEqual({
    ok: false,
    error: { service: "registry-service", kind: "bad-answer" },
  });
});

test("getPlot returns the parsed plot", async () => {
  stubRegistry({ "/v1/plots/a": () => reply(plot("a", "f1")) });
  expect(await getPlot("a")).toEqual({
    ok: true,
    data: { id: "a", farmId: "f1", name: "Plot a", cropId: "tomato", areaM2: 1000 },
  });
});

test("getPlot passes a 404 through, and encodes the id", async () => {
  const fake = stubRegistry({ "/v1/plots/..%2Fhealth": () => reply({ code: "NOT_FOUND" }, 404) });
  expect(await getPlot("../health")).toMatchObject({ ok: false, error: { kind: "problem", status: 404 } });
  expect(fake.mock.calls[0][0]).toBe("http://registry/v1/plots/..%2Fhealth");
});
