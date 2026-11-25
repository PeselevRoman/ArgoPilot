// Tests for the demo stand-in services. Run from the repository root:
//   node --test scripts/demo/stubs.test.mjs
// They start the stand-in on free ports and call it over HTTP. No real service is involved.
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, before, test } from "node:test";
import { fileURLToPath } from "node:url";
import { FARMS, PLOTS, start } from "./stubs.mjs";

const NORTH = "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002";
const SEED = fileURLToPath(new URL("../../tasks/seed_registry.sh", import.meta.url));
// The engine's answers (written by services/planner-service/demo_numbers.py).
const NUMBERS = JSON.parse(readFileSync(new URL("./plan_numbers.json", import.meta.url), "utf8"));
const planOf = (scenario, id) => NUMBERS.scenarios[scenario][id].days;

let demo;
const url = (name, path) => `http://127.0.0.1:${demo.ports[name]}${path}`;
const setState = (state) => fetch(url("control", `/state/${state}`));
const plan = async (id = NORTH) => {
  const res = await fetch(url("planner", `/v1/plots/${id}/plan?days=7`));
  return { res, body: await res.json() };
};

before(async () => {
  demo = await start({ ports: { registry: 0, weather: 0, planner: 0, control: 0 } });
});
after(() => demo.close());
test.beforeEach(() => setState("reset"));

test("the default state is water: each plot gets the engine's water plan, 7 days", async () => {
  for (const plotId of PLOTS.map((p) => p.id)) {
    const { res, body } = await plan(plotId);
    assert.equal(res.status, 200);
    assert.equal(body.plot_id, plotId);
    assert.deepEqual(body.days, planOf("water", plotId));
    assert.equal(body.days.length, 7);
  }
});

test("the water plan of the North block: its dates, and irrigation today (day 1) and on day 6", async () => {
  const { body } = await plan();
  assert.deepEqual(
    body.days.map((d) => d.date),
    ["2026-11-27", "2026-11-28", "2026-11-29", "2026-11-30", "2026-12-01", "2026-12-02", "2026-12-03"],
  );
  // The headline is the first day, so today's panel is the blue "water" one.
  assert.ok(body.days[0].litres > 0);
  assert.deepEqual(
    body.days.filter((d) => d.litres > 0).map((d) => d.date),
    ["2026-11-27", "2026-12-02"],
  );
  assert.ok(body.days.every((d) => d.stale === false));
});

test("every day has exactly the seven fields of the planner's answer", async () => {
  const { body } = await plan();
  for (const day of body.days) {
    assert.deepEqual(Object.keys(day).sort(), ["bucket_mm", "date", "et0_mm", "kc", "litres", "run_minutes", "stale"]);
  }
});

test("numbers are rounded like the real planner: 2 decimals, kc 3", async () => {
  for (const state of ["water", "full", "stale"]) {
    await setState(state);
    const { body } = await plan();
    for (const day of body.days) {
      for (const key of ["et0_mm", "litres", "run_minutes", "bucket_mm"]) {
        assert.equal(day[key], Math.round(day[key] * 100) / 100, `${state} ${key}`);
      }
      assert.equal(day.kc, Math.round(day.kc * 1000) / 1000);
    }
  }
});

test("full: each plot gets the engine's plan for its seed planting date", async () => {
  await setState("full");
  for (const plotId of PLOTS.map((p) => p.id)) {
    const { body } = await plan(plotId);
    assert.deepEqual(body.days, planOf("full", plotId));
  }
  // The North block was planted in March, so it is past its season: no irrigation at all.
  const { body } = await plan();
  assert.ok(body.days.every((d) => d.litres === 0 && d.run_minutes === 0 && d.stale === false));
});

test("stale: all 7 days are stale, like the real planner (one flag for the whole forecast)", async () => {
  await setState("stale");
  const { res, body } = await plan();
  assert.equal(res.status, 200);
  assert.equal(body.days.length, 7);
  assert.ok(body.days.every((d) => d.stale === true));
  assert.deepEqual(body.days, planOf("stale", NORTH));
});

test("weather-down: the weather health fails, and the planner answers 503 naming the weather service", async () => {
  await setState("weather-down");
  assert.equal((await fetch(url("weather", "/health"))).status, 503);
  assert.equal((await fetch(url("registry", "/health"))).status, 200);
  assert.equal((await fetch(url("planner", "/health"))).status, 200);
  const { res, body } = await plan();
  assert.equal(res.status, 503);
  assert.match(res.headers.get("content-type"), /application\/problem\+json/);
  assert.equal(body.code, "UPSTREAM_UNAVAILABLE");
  assert.match(body.detail, /weather-service/);
});

test("registry-down: the registry does not answer, and the planner answers 503 naming the registry", async () => {
  await setState("registry-down");
  await assert.rejects(fetch(url("registry", "/health")));
  assert.equal((await fetch(url("weather", "/health"))).status, 200);
  const { res, body } = await plan();
  assert.equal(res.status, 503);
  assert.equal(body.code, "UPSTREAM_UNAVAILABLE");
  assert.match(body.detail, /registry-service/);
});

test("reset goes back to water", async () => {
  await setState("weather-down");
  const reply = await setState("reset");
  assert.deepEqual(await reply.json(), { state: "water" });
  assert.equal((await fetch(url("weather", "/health"))).status, 200);
});

test("an unknown state is a 404 problem that lists the valid ones, and changes nothing", async () => {
  await setState("stale");
  const res = await setState("nope");
  assert.equal(res.status, 404);
  const body = await res.json();
  assert.equal(body.code, "NOT_FOUND");
  assert.match(body.detail, /water/);
  assert.match(body.detail, /registry-down/);
  assert.deepEqual(await (await fetch(url("control", "/state"))).json(), { state: "stale", states: body.states });
});

test("the registry lists farms and plots, and one plot by id", async () => {
  const farms = await (await fetch(url("registry", "/v1/farms"))).json();
  const plots = await (await fetch(url("registry", "/v1/plots"))).json();
  assert.ok(farms.length >= 2 && farms.every((f) => f.id && f.name));
  assert.equal(plots.length, 4);
  for (const p of plots) {
    assert.ok(farms.some((f) => f.id === p.farm_id), "every plot belongs to a listed farm");
    assert.deepEqual(Object.keys(p).sort(), ["area_m2", "crop_id", "farm_id", "id", "name"]);
  }
  const one = await fetch(url("registry", `/v1/plots/${NORTH}`));
  assert.equal(one.status, 200);
  assert.equal((await one.json()).id, NORTH);
});

test("the stand-in's farms and plots are the rows of tasks/seed_registry.sh", (t) => {
  if (spawnSync("sqlite3", ["-version"]).error) {
    t.skip("sqlite3 is not installed, and the seed script needs it");
    return;
  }
  const dir = mkdtempSync(join(tmpdir(), "stub-seed-"));
  try {
    const db = join(dir, "registry.db");
    const seeded = spawnSync("bash", [SEED, db], { encoding: "utf8" });
    assert.equal(seeded.status, 0, seeded.stderr);
    const query = (sql) => {
      const out = spawnSync("sqlite3", ["-json", db, sql], { encoding: "utf8" });
      assert.equal(out.status, 0, out.stderr);
      return out.stdout.trim() ? JSON.parse(out.stdout) : [];
    };
    const byId = (a, b) => (a.id < b.id ? -1 : 1);
    const seedFarms = query("SELECT id, name FROM farms").sort(byId);
    const seedPlots = query("SELECT id, farm_id, name, crop_id, area_m2 FROM plots").sort(byId);
    assert.deepEqual([...FARMS].sort(byId), seedFarms);
    assert.deepEqual([...PLOTS].sort(byId), seedPlots);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
});

test("an unknown plot is a 404 problem from the registry and from the planner", async () => {
  const fromRegistry = await fetch(url("registry", "/v1/plots/nope"));
  assert.equal(fromRegistry.status, 404);
  assert.equal((await fromRegistry.json()).code, "NOT_FOUND");
  const { res, body } = await plan("nope");
  assert.equal(res.status, 404);
  assert.equal(body.code, "NOT_FOUND");
});
