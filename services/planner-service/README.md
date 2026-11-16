# planner-service

Builds irrigation plans. It calls registry-service (plots and crops) and weather-service (ET0 and rain) over HTTP and combines them. It has no database.

## Setup and run

```bash
cd services/planner-service
uv sync                    # creates .venv and installs dependencies
cp .env.example .env       # then edit the values if needed (never committed)
uv run uvicorn main:app --host 127.0.0.1 --port 8002
```

The service refuses to start, with a clear error naming the variable, if a required setting is missing or invalid.

## Tests

```bash
uv run pytest -q
```
