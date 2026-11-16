# weather-service

AgroPilot weather service (work in progress).

## Setup

```bash
cd services/weather-service
uv sync                    # creates .venv and installs dependencies
cp .env.example .env       # then edit the values if needed
```

## Run

```bash
uv run uvicorn main:app --host 127.0.0.1 --port 8001
```

## Test

```bash
uv run pytest -q
```
