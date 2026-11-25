# frontend: design

Decisions are recorded only in `docs/judgment-log-p2.md`. This file describes the design and does not restate the reasoning. Nothing about the frontend is logged yet; pending entries are listed at the end.

Source of requirements: `tasks/p2.md`, section "The `frontend`" (FR-2.15 to FR-2.19, NFR-2.8) and "Global configurations".

## Intent

A grower will not use `curl`. The frontend is a small web app that shows the farms, their plots, and today's irrigation recommendation with the 7-day plan. It is read in the field, on a phone, often outdoors. The value of the app is that the answer to "should I water this plot today, and for how many minutes?" is the first thing on the plot page, and that a failure is explained in plain words instead of showing a blank page or a stack trace.

## Goals

- `/` lists every farm with its plots. Each plot links to `/plots/{id}` (FR-2.15).
- `/plots/{id}` shows today's recommendation first, large ("Water for 38 minutes" or "No irrigation today"), then the 7-day plan (FR-2.16).
- A stale forecast is shown next to the numbers it affects, per day (FR-2.17).
- A planner error shows what happened, for example which service is down (FR-2.18).
- A status line shows whether registry, weather and planner are up, from `GET /health` (FR-2.19).
- At 375 px width: no horizontal scrolling, and today's recommendation is visible without scrolling (NFR-2.8).

## Non-goals and anti-goals

- No other pages or features: no create/edit/delete of farms or plots, no login, no settings page, no charts, no live polling.
- The browser never calls a service. No route handlers, no client-side data fetching.
- The frontend never computes, rounds again, or adjusts an irrigation number (CLAUDE.md rule 12). It shows the planner's numbers as given.
- Anti-goals: a blank page, a stack trace, or a service URL or port shown to the user. A plan of zeros shown when the planner failed. A stale day that looks like a fresh one.

## Constraints

- Next.js (App Router, TypeScript), Tailwind CSS, shadcn/ui, in `services/frontend`. Node 22.
- All calls to the services live in `src/lib/`. Pages are Server Components that fetch on the server.
- `REGISTRY_URL`, `WEATHER_URL`, `PLANNER_URL` come from `.env.local` (never committed). `.env.example` is committed and complete.
- `npm run build` and `npm run lint` pass.
- The `frontend-design` skill is used for the look.
- `services/frontend` is committed without `node_modules/`, `.next/` or `.env.local`.

## Approaches considered

- **A. Server Components calling the services through `src/lib/` (chosen).** The browser receives HTML only. Matches the spec's rule that the browser never calls the services, and needs no client state.
- **B. Route handlers as a proxy, with client-side fetch.** Rejected: adds routes the spec does not list, and needs spinners and client state.
- **C. Client-side polling of the status line.** Rejected: a feature outside the spec.

## What the frontend consumes

| Call | Used for | Answer |
|---|---|---|
| registry `GET /v1/farms` | the farm list | array of `{id, name}` |
| registry `GET /v1/plots` | the plots of all farms, grouped by `farm_id` on the page | array of plots (`id`, `farm_id`, `name`, `crop_id`, `area_m2`, and so on) |
| registry `GET /v1/plots/{id}` | the plot's name and crop for the plot page title | one plot, or `404 NOT_FOUND` |
| planner `GET /v1/plots/{id}/plan?days=7` | the recommendation and the plan | `{plot_id, days: [{date, et0_mm, kc, litres, run_minutes, stale, bucket_mm}]}` |
| each service `GET /health` | the status line | `{"status": "ok"}` |

Weather is only called for its `/health`. The frontend never asks it for a forecast: the planner does that.

## Behavior

**`/`.** Farms with their plots. If the registry fails, the page says the registry is not available, with no farms listed. An empty farm says it has no plots. A plot link goes to `/plots/{id}`.

**`/plots/{id}`.** The page asks the registry for the plot and the planner for the 7-day plan, at the same time.

| Situation | What the grower sees |
|---|---|
| Plan received, today's `run_minutes` above 0 | "Water for N minutes", and today's litres |
| Plan received, today's `run_minutes` 0 | "No irrigation today" |
| A day with `stale: true` | a stale marker on that day's row and on the recommendation if it is today, with a short plain explanation. Never a different number |
| Planner `404 NOT_FOUND` | "This plot does not exist", with a link back to `/` |
| Planner `503 UPSTREAM_UNAVAILABLE` | the planner's `detail` rewritten in plain words, naming the service ("weather-service is not available"). No plan is shown |
| Planner `503 UNAVAILABLE`, `422`, a timeout, a network failure, or an answer that is not a valid plan | "The plan is not available right now", naming the planner. No plan is shown, no stack trace |

The plan shows, for each of the days: date, `run_minutes`, `litres`, and the stale marker. It also shows `et0_mm`, `kc` and `bucket_mm` as secondary numbers (the learner asked for `bucket_mm` to be shown for now and will decide after seeing it on different devices). A day with no irrigation reads as "no irrigation".

**Status line.** Shown on both pages. It checks the three `/health` endpoints, each with its own timeout, and shows up or down per service. A service that does not answer in time shows as down. It loads on its own, so a slow service never delays the page.

**Validation in `src/lib/`.** An answer is used only if it has the expected shape: required fields, right types, finite numbers, the planner's `days` non-empty. Anything else is treated as that service being unavailable, never repaired or defaulted. This follows the same rule the planner applies to its own upstreams.

## Configuration

| Variable | Meaning |
|---|---|
| `REGISTRY_URL` | base URL of registry-service |
| `WEATHER_URL` | base URL of weather-service |
| `PLANNER_URL` | base URL of planner-service |
| `REQUEST_TIMEOUT_MS` | timeout for every call to a service (my call: a fourth variable beyond the spec's three) |

No defaults in code. If one is missing or invalid, the app stops with a message naming the variable, like the Python services. `.env.example` lists all four with safe example values.

## Caching

No caching. Every page load asks the services again (`no-store`), because a plan changes daily and the status line must be live.

## Look and feel

Decided later, in the design plan the `frontend-design` skill asks for (colours, type, layout and wireframes), and shown to the learner before the UI is built. Constraints from the brief: read outdoors on a phone, so high contrast and large type; today's recommendation is the memorable element and everything else stays quiet; the stale warning and the error state are clearly different from each other and from normal; the structure follows the real content (7 consecutive days, no 7-column table at 375 px).

## Tests

Vitest. Unit tests for `src/lib/` (response validation, error mapping, timeout, stale handling, config loading) with the services replaced by a fake `fetch`, never a real network. Component tests for the recommendation, the plan rows and the status line in each state: water, no water, stale, 404, 503 naming a service, an invalid answer, a service down. The build and lint are separate checks. A manual check at 375 px is part of the final review (NFR-2.8).

## Left to the builder

Folder layout under `src/`, component names, and the exact wording of the messages, within the rules above. The frontend's look comes from the design plan.

## Pending judgment-log entries

To be proposed to the learner when each comes up, not yet written:

- The frontend calls only the services through server code, and has a fourth variable, `REQUEST_TIMEOUT_MS`.
- No caching, and the status line loads on its own.
- An invalid answer from a service is treated as that service being down.
- Every plan day shows `bucket_mm`, for now (the learner's choice, to be revisited after the device check).
