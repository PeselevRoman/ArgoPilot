// Tests for the demo stand-in services. Run from the repository root:
//   node --test scripts/demo/stubs.test.mjs
// They start the stand-in on free ports and call it over HTTP. No real service is involved.
import assert from "node:assert/strict";
import { after, before, test } from "node:test";
import { start } from "./stubs.mjs";

let demo;
const url = (name, path) => `http://127.0.0.1:${demo.ports[name]}${path}`;
const setState = (state) => fetch(url("control", `/state/${state}`));
const plan = async (id = "p1") => {
  const res = await fetch(url("planner", `/v1/plots/${id}/plan?days=7`));
  return { res, body: await res.json() };
};

before(async () => {
  demo = await start({
    ports: { registry: 0, weather: 0, planner: 0, control: 0 },
    today: "2026-11-27",
  });
});
after(() => demo.close());
test.beforeEach(() => setState("reset"));

test("the default state is water: 7 days from today, today and day 4 irrigate", async () => {
  const { res, body } = await plan();
  assert.equal(res.status, 200);
  assert.equal(body.plot_id, "p1");
  assert.equal(body.days.length, 7);
  assert.deepEqual(
    body.days.map((d) => d.date),
    ["2026-11-27", "2026-11-28", "2026-11-29", "2026-11-30", "2026-12-01", "2026-12-02", "2026-12-03"],
  );
  assert.equal(body.days[0].run_minutes, 341.55);
  assert.equal(body.days[0].litres, 18975);
  assert.equal(body.days[1].run_minutes, 0);
  assert.equal(body.days[3].run_minutes, 341.55);
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

test("full: no day irrigates", async () => {
  await setState("full");
  const { body } = await plan();
  assert.ok(body.days.every((d) => d.litres === 0 && d.run_minutes === 0 && d.stale === false));
});

test("stale: all 7 days are stale, like the real planner (one flag for the whole forecast)", async () => {
  await setState("stale");
  const { res, body } = await plan();
  assert.equal(res.status, 200);
  assert.equal(body.days.length, 7);
  assert.ok(body.days.every((d) => d.stale === true));
  assert.equal(body.days[0].run_minutes, 341.55);
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
  assert.ok(plots.length >= 3);
  for (const p of plots) {
    assert.ok(farms.some((f) => f.id === p.farm_id), "every plot belongs to a listed farm");
    assert.deepEqual(Object.keys(p).sort(), ["area_m2", "crop_id", "farm_id", "id", "name"]);
  }
  const one = await fetch(url("registry", "/v1/plots/p1"));
  assert.equal(one.status, 200);
  assert.equal((await one.json()).id, "p1");
});

test("an unknown plot is a 404 problem from the registry and from the planner", async () => {
  const fromRegistry = await fetch(url("registry", "/v1/plots/nope"));
  assert.equal(fromRegistry.status, 404);
  assert.equal((await fromRegistry.json()).code, "NOT_FOUND");
  const { res, body } = await plan("nope");
  assert.equal(res.status, 404);
  assert.equal(body.code, "NOT_FOUND");
});
