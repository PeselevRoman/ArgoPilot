// Stand-in registry, weather and planner for the P2 demo. NOT the real services.
//
// Why it exists: the real planner starts every plan with a full soil bucket, so it never says
// "water today", and a stale forecast needs Open-Meteo to fail. This stand-in gives the frontend
// canned answers for each state, so every screen can be shown on demand. The numbers are fixed
// examples (the hand-calculated case 1 of the irrigation-calc-reference skill). Nothing here
// calculates an irrigation number.
//
// Run:      node scripts/demo/stubs.mjs
// Switch:   curl localhost:8199/state/<water|full|stale|weather-down|registry-down|reset>
import http from "node:http";
import { pathToFileURL } from "node:url";

export const STATES = ["water", "full", "stale", "weather-down", "registry-down"];

const FARMS = [
  { id: "f1", name: "Demo farm" },
  { id: "f2", name: "Greenhouse farm" },
];
const PLOTS = [
  { id: "p1", farm_id: "f1", name: "North block", crop_id: "tomato", area_m2: 1000 },
  { id: "p2", farm_id: "f1", name: "East block", crop_id: "bell-pepper", area_m2: 800 },
  { id: "p3", farm_id: "f2", name: "Greenhouse", crop_id: "tomato", area_m2: 300 },
];

// Canned numbers, already rounded the way the real planner rounds (2 decimals, kc 3).
const ET0 = [2.69, 3.03, 3.17, 3.09, 2.65, 2.74, 2.57];
const WATER = {
  kc: 1.15,
  irrigates: [true, false, false, true, false, false, false],
  bucket: [51.2, 45.3, 39.1, 51.2, 44.4, 38.2, 32.1],
};
const FULL = {
  kc: 0.8,
  irrigates: [false, false, false, false, false, false, false],
  bucket: [120.29, 117.92, 115.39, 112.92, 110.8, 108.52, 106.46],
};

function addDays(isoDate, days) {
  const date = new Date(`${isoDate}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function planDays(state, today) {
  const curve = state === "full" ? FULL : WATER;
  return ET0.map((et0, i) => ({
    date: addDays(today, i),
    et0_mm: et0,
    kc: curve.kc,
    litres: curve.irrigates[i] ? 18975 : 0,
    run_minutes: curve.irrigates[i] ? 341.55 : 0,
    // The weather service sends one stale flag for the whole forecast, so every day is stale.
    stale: state === "stale",
    bucket_mm: curve.bucket[i],
  }));
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

// Start the four servers. `ports` are 0 in the tests (any free port); `today` can be fixed there.
export async function start({ ports = {}, today = new Date().toISOString().slice(0, 10) } = {}) {
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
    return send(res, 200, { plot_id: id, days: planDays(state, today) });
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
