# frontend

The grower's web app: the farms and their plots, today's irrigation recommendation, and the 7-day plan. Built with Next.js 16.4.6 (App Router, TypeScript), Tailwind CSS and shadcn/ui.

The browser never calls the services. Pages are rendered on the server, and every call to a service lives in `src/lib/`.

## Setup

```bash
cd services/frontend
cp .env.example .env.local     # then edit the values if needed (never committed)
npm install
npm run dev                    # http://localhost:3000
```

The app refuses to start, with a message naming the variable, if a variable in `.env.local` is missing or invalid. The registry (8000), weather (8001) and planner (8002) services must be running for the pages to show data.

| Variable | Meaning |
| --- | --- |
| `REGISTRY_URL` | base URL of registry-service |
| `WEATHER_URL` | base URL of weather-service (only `/health` is called) |
| `PLANNER_URL` | base URL of planner-service |
| `REQUEST_TIMEOUT_MS` | how long to wait for any service, in milliseconds |

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | development server |
| `npm test` | Vitest tests (`tests/`), with a fake `fetch`, no real network |
| `npm run lint` | ESLint |
| `npm run build` | production build and type check |

## How it was checked

- `npm test`: 139 tests (parsing, error messages, health, recommendation, formatting, components), with a fake `fetch`.
- `npm run lint` and `npm run build` pass.
- Against stand-in services (a small script that played the registry, weather and planner), the pages were fetched and their text read for each case: water today, no irrigation, stale forecast (marker only on the affected days), weather service down (named in the message), the planner sending an empty plan, an unknown plot, the registry down (on `/` and on a plot), and a planner that never answers (message after the timeout). The status line followed each service going down.
- The app refuses to start with a clear message when a variable such as `REGISTRY_URL` is missing.

Not checked here: the layout at 375 px (NFR-2.8). Open the page in the browser, right click, Inspect, then the device toolbar, and pick a phone. Check that there is no horizontal scroll and that today's recommendation is visible without scrolling.
