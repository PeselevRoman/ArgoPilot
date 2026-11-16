// NFR-2.3: a fresh forecast (no provider call) is answered with p95 at most 100 ms at 10 requests per second.
//
// Run from the repository root, after starting the server with perf/run_weather_server.py:
//     k6 run --summary-export summary.json perf/weather_nfr_2_3.js

import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8011";

export const options = {
  scenarios: {
    fresh_forecast: {
      executor: "constant-arrival-rate",
      rate: 10,
      timeUnit: "1s",
      duration: "60s",
      preAllocatedVUs: 10,
      maxVUs: 50,
    },
  },
  thresholds: {
    http_req_duration: ["p(95)<=100"],
    http_req_failed: ["rate==0"],
  },
};

// One request before the run fills the cache, so every measured request is a fresh hit.
export function setup() {
  const response = http.get(`${BASE}/v1/forecast?lat=31.25&lon=34.75&days=7`);
  check(response, { "warm-up is 200": (r) => r.status === 200 });
}

export default function () {
  // Random points inside one 0.1 degree cell (31.2..31.3, 34.7..34.8): they all share one forecast.
  const lat = (31.2 + Math.random() * 0.099).toFixed(3);
  const lon = (34.7 + Math.random() * 0.099).toFixed(3);
  const response = http.get(`${BASE}/v1/forecast?lat=${lat}&lon=${lon}&days=7`);
  check(response, {
    "status is 200": (r) => r.status === 200,
    "not stale": (r) => r.json("stale") === false,
    "seven days": (r) => r.json("days").length === 7,
  });
}
