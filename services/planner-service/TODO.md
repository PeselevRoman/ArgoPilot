# planner-service: TODO

Ideas for the final product. They are **out of scope for P2**: the assignment lists exactly what the planner returns, and these need a new input or a new endpoint. Each one is a rule the planner currently fixes by judgment (see the README, "Stated approximations", and `docs/judgment-log-p2.md`).

## 1. Let the grower say how full the bucket is today

**Now:** the plan assumes the bucket is full at the start of today (depletion 0), because the planner keeps no irrigation history. If the field is really dry, day 1 under-recommends.

**Make it configurable, either way:**
- Add an optional query parameter to `GET /v1/plots/{id}/plan`, for example `start_depletion_mm` (or a fraction of the bucket), used as `Dr` at the start of day 1. A missing value keeps today's behaviour.
- Or add a new endpoint that records what actually happened, for example `POST /v1/plots/{id}/irrigations` (date, litres or minutes), and let the planner work out the starting depletion from the recorded irrigations and the past weather. This needs a place to store history (the registry, or a new service) and a historical weather source, so it is the bigger change.

## 2. Let the grower say what season a plot is in

**Now:** the Kc curve counts days from `planting_date`. A plot past its season (for example every demo plot today) keeps the last Kc (`Kc_end`) for all later days, so its plan is low and probably meaningless, because the crop is likely harvested.

**Make it configurable, either way:**
- Change the registry plot to carry a season (a planting date that the grower updates for each crop cycle, and an optional harvest date), and make the planner return an explicit answer after harvest (for example no irrigation, with a clear reason) instead of using `Kc_end`.
- Or add an optional query parameter to the plan endpoint to override the planting date, for planning a hypothetical crop.

Both need a decision on the plan JSON, since the course fixes the per-day fields (`date`, `et0_mm`, `kc`, `litres`, `run_minutes`, `stale`, `bucket_mm`).

## 3. Keep the last good registry data for a limited time, so a registry outage does not stop every plan

**Now:** the planner does not retry or cache. If registry-service is down or does not answer in time, the plan is `503 UPSTREAM_UNAVAILABLE`, and the frontend shows "the registry is not available". This is on purpose: the registry is the source of truth, and a plan built from guessed data could mean wrong irrigation (see `docs/judgment-log-p2.md`, "The planner waits 5 s for the registry and 45 s for weather").

**Make it more resilient:**
- Keep the last good plot, soil and emitter data in the planner's memory, and use it for a limited time (for example 24 hours, like the weather forecast) when the registry fails. Mark the plan as built from old data, as `stale` does for weather, so the grower can see it. A small in-memory cache in the planner is simpler than a separate caching service, which would be one more thing that can be down.
- Risks to decide on first: a plot the grower just edited (crop, emitter, area) would be planned from its old values; only plots opened before the outage are cached; and the plan JSON has no field to say the registry data is old, so this needs a decision on the response, as the weather `stale` flag did.
- A cheaper first step is one short retry of the registry call, which covers brief blips but not a real outage.
- Measure how often the registry is actually down before building any of this.
