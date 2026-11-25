# weather-service: TODO

Ideas for the final product. They are **out of scope for P2**. Ideas that reach across services are in the root [`TODO.md`](../../TODO.md).

## 1. Handle a rate-limit answer (`429`) from Open-Meteo on its own

**Now:** `provider.fetch` in `provider.py` treats every non-success status the same. A `429 Too Many Requests` becomes a `ProviderError` like a `500` or a timeout, so the service retries it twice, 0.5 s apart (see "The weather service retries twice, then falls back to the stale forecast, then refuses" in `docs/judgment-log-p2.md`). That is the wrong reaction to a rate limit: the retries send more requests to a provider that has just said there are too many, and any `Retry-After` header the provider sends is ignored. The result for the user is still safe (the stale forecast, or `503`), so this is a fix, not a bug in the answers.

**Make it behave:**
- Recognise `429` as its own kind of failure, and do not retry it within the same request.
- Read `Retry-After` when the provider sends it, and remember it: do not call the provider again for that long. During that time, serve the stale forecast or `503` straight away. This needs a small piece of state in the service (one "blocked until" time), and the shared fetch must respect it.
- The assignment says nothing about this, so the wait time and the cap on it (a provider could send a huge `Retry-After`) are new decisions for the judgment log. Check Open-Meteo's current documentation for its limits and how it signals them; they change over time.
- Tests with the fake provider: a `429` is not retried, a `Retry-After` blocks later calls until the time has passed, and the answer is the stale forecast or `503` in the meantime.
- Related gap: after any failure, the service remembers nothing, so every later request starts a new retry chain (see "Concurrent requests for one cell share a single provider fetch" in the log). A short back-off after failures could cover both cases.
