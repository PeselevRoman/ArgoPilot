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
