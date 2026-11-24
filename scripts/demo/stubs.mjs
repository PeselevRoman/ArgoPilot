// Stand-in registry, weather and planner for the P2 demo. NOT the real services.
//
// Why it exists: the real planner starts every plan with a full soil bucket, so it never says
// "water today" for a plot past its season, and a stale forecast needs Open-Meteo to fail. This
// stand-in gives the frontend fixed answers for each state, so every screen can be shown on demand.
// The plan numbers are NOT typed here: they are in plan_numbers.json, written by the real engine
// (services/planner-service/demo_numbers.py). In the water state each plot starts partly dry, by a
// stated field-check value (see that script), so today's panel shows irrigation. Nothing in this
// file calculates an irrigation number.
//
// Run:      node scripts/demo/stubs.mjs
// Switch:   curl localhost:8199/state/<water|full|stale|weather-down|registry-down|reset>
import { readFileSync } from "node:fs";
import http from "node:http";
import { pathToFileURL } from "node:url";

export const STATES = ["water", "full", "stale", "weather-down", "registry-down"];

// The farms and plots are the rows of tasks/seed_registry.sh, copied here. stubs.test.mjs fails if
// they drift from that file.
export const FARMS = [
  { id: "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001", name: "Demo cooperative" },
  { id: "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004", name: "East farm" },
];
export const PLOTS = [
  { id: "c8f3d1b0-4d2e-5a1b-8b22-1d6e3f702002", farm_id: "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001", name: "North block", crop_id: "tomato", area_m2: 1000 },
  { id: "d9a4e2c1-5e3f-4b6a-9c33-2e7f4a803003", farm_id: "b7e2c0a0-3c1d-4f0a-9a11-0c5d2e6f1001", name: "East block", crop_id: "bell-pepper", area_m2: 800 },
  { id: "e0b5f3d2-6f40-4c7b-8d44-3f8a5b914004", farm_id: "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004", name: "West block", crop_id: "tomato", area_m2: 1500 },
  { id: "f1c6a4e3-7051-4d8c-9e55-4a9b6c025005", farm_id: "a9c1e4b2-6f70-4d8e-a144-3f8b5c904004", name: "Greenhouse", crop_id: "bell-pepper", area_m2: 400 },
];

// The engine's answers, written by demo_numbers.py: scenarios "water", "stale" and "full", each
// keyed by plot id. Rounded like the real planner (2 decimals, kc 3).
const NUMBERS = JSON.parse(readFileSync(new URL("./plan_numbers.json", import.meta.url), "utf8"));

// The state picks the scenario. "water" is the default, and the registry and weather states
// reuse the water plan (they fail before a plan is sent, so they never show it).
function planFor(state, plotId) {
  const scenario = state === "full" || state === "stale" ? state : "water";
  const entry = NUMBERS.scenarios[scenario][plotId];
  return { plot_id: plotId, days: entry.days };
}

function send(res, status, body, type = "application/json") {
  res.writeHead(status, { "content-type": type });
  res.end(JSON.stringify(body));
}
const problem = (res, status, code, detail, extra = {}) =>
  send(res, status, { code, detail, ...extra }, "application/problem+json");

function listen(handler, port) {
  return new Promise((resolve) => {
    const server = http.createServer(handler);
    server.listen(port, "127.0.0.1", () => resolve(server));
  });
}

// Start the four servers. `ports` are 0 in the tests (any free port).
export async function start({ ports = {} } = {}) {
  let state = "water";
  const wanted = { registry: 8100, weather: 8101, planner: 8102, control: 8199, ...ports };

  const registry = await listen((req, res) => {
    if (state === "registry-down") return req.socket.destroy(); // no answer at all
    const { pathname } = new URL(req.url, "http://x");
    if (pathname === "/health") return send(res, 200, { status: "ok" });
    if (pathname === "/v1/farms") return send(res, 200, FARMS);
    if (pathname === "/v1/plots") return send(res, 200, PLOTS);
    const match = pathname.match(/^\/v1\/plots\/(.+)$/);
    const plot = match && PLOTS.find((p) => p.id === decodeURIComponent(match[1]));
    if (plot) return send(res, 200, plot);
    return problem(res, 404, "NOT_FOUND", "Plot not found");
  }, wanted.registry);

  const weather = await listen((req, res) => {
    const { pathname } = new URL(req.url, "http://x");
    if (pathname !== "/health") return problem(res, 404, "NOT_FOUND", "Not found");
    if (state === "weather-down") return problem(res, 503, "UNAVAILABLE", "The weather service is down");
    return send(res, 200, { status: "ok" });
  }, wanted.weather);

  const planner = await listen((req, res) => {
    const { pathname } = new URL(req.url, "http://x");
    if (pathname === "/health") return send(res, 200, { status: "ok" });
    const match = pathname.match(/^\/v1\/plots\/(.+)\/plan$/);
    if (!match) return problem(res, 404, "NOT_FOUND", "Not found");
    const id = decodeURIComponent(match[1]);
    if (!PLOTS.some((p) => p.id === id)) return problem(res, 404, "NOT_FOUND", "Plot not found");
    if (state === "registry-down" || state === "weather-down") {
      const service = state === "registry-down" ? "registry-service" : "weather-service";
      return problem(res, 503, "UPSTREAM_UNAVAILABLE", `${service} is unavailable: ConnectError`);
    }
    return send(res, 200, planFor(state, id));
  }, wanted.planner);

  const control = await listen((req, res) => {
    const { pathname } = new URL(req.url, "http://x");
    if (pathname === "/state") return send(res, 200, { state, states: [...STATES, "reset"] });
    const match = pathname.match(/^\/state\/(.+)$/);
    if (!match) return problem(res, 404, "NOT_FOUND", "Use /state/<name>");
    const name = match[1] === "reset" ? "water" : match[1];
    if (!STATES.includes(name)) {
      return problem(res, 404, "NOT_FOUND", `Unknown state. Use one of: ${[...STATES, "reset"].join(", ")}`, {
        states: [...STATES, "reset"],
      });
    }
    state = name;
    return send(res, 200, { state });
  }, wanted.control);

  const servers = { registry, weather, planner, control };
  return {
    ports: Object.fromEntries(Object.entries(servers).map(([k, s]) => [k, s.address().port])),
    close: () => Promise.all(Object.values(servers).map((s) => new Promise((done) => s.close(done)))),
  };
}

// Run directly: start on the fixed ports and print what to do.
if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const demo = await start();
  console.log("Stand-in services running (canned answers, not the real services):");
  console.log(`  registry  http://127.0.0.1:${demo.ports.registry}`);
  console.log(`  weather   http://127.0.0.1:${demo.ports.weather}`);
  console.log(`  planner   http://127.0.0.1:${demo.ports.planner}`);
  console.log(`  control   http://127.0.0.1:${demo.ports.control}`);
  console.log(`Switch state: curl localhost:${demo.ports.control}/state/<${STATES.join("|")}|reset>`);
  console.log("Start state: water. Press Ctrl+C to stop.");
}
