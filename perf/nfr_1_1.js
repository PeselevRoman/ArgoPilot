// NFR-1.1: p95 of the list and get-by-id routes is at most 100 ms at 10 requests per second.
// Each endpoint is measured on its own, one after another, so the runs do not compete.
//
// Run from the repository root, after starting the server with perf/run_server.py:
//     k6 run perf/nfr_1_1.js

import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8001";
const RATE = 10;
const DURATION = "60s";
const SLOT = 70; // seconds between the start of each endpoint's run

function scenario(name, startSlot) {
  return {
    executor: "constant-arrival-rate",
    rate: RATE,
    timeUnit: "1s",
    duration: DURATION,
    preAllocatedVUs: 10,
    maxVUs: 50,
    startTime: `${startSlot * SLOT}s`,
    exec: name,
  };
}

export const options = {
  scenarios: {
    list_farms: scenario("listFarms", 0),
    get_farm: scenario("getFarm", 1),
    list_plots: scenario("listPlots", 2),
    get_plot: scenario("getPlot", 3),
  },
  thresholds: {
    "http_req_duration{endpoint:list_farms}": ["p(95)<100"],
    "http_req_duration{endpoint:get_farm}": ["p(95)<100"],
    "http_req_duration{endpoint:list_plots}": ["p(95)<100"],
    "http_req_duration{endpoint:get_plot}": ["p(95)<100"],
    http_req_failed: ["rate==0"],
  },
};

// Runs once before the scenarios. It reads the real ids the get-by-id routes will use.
export function setup() {
  const farms = http.get(`${BASE}/v1/farms`).json();
  const plots = http.get(`${BASE}/v1/plots`).json();
  return {
    farmIds: farms.map((farm) => farm.id),
    plotIds: plots.map((plot) => plot.id),
  };
}

function pick(ids) {
  return ids[Math.floor(Math.random() * ids.length)];
}

function get(url, endpoint) {
  const response = http.get(url, { tags: { endpoint: endpoint } });
  check(response, { "status is 200": (r) => r.status === 200 });
}

export function listFarms() {
  get(`${BASE}/v1/farms`, "list_farms");
}

export function getFarm(data) {
  get(`${BASE}/v1/farms/${pick(data.farmIds)}`, "get_farm");
}

export function listPlots() {
  get(`${BASE}/v1/plots`, "list_plots");
}

export function getPlot(data) {
  get(`${BASE}/v1/plots/${pick(data.plotIds)}`, "get_plot");
}
