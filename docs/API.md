http://127.0.0.1:5500http://127.0.0.1:5500http://127.0.0.1:5500# API

The local backend runs at `http://127.0.0.1:8000`. Start it with:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\run_backend.py
```

Interactive documentation is available at
`http://127.0.0.1:8000/docs`.

## Endpoints

- `GET /health` - read-only database health check.
- `GET /api/summary?city=Delhi` - latest verified observation, pollutant
  values, data range, recent AQI trend, and the next 48 AQI forecasts when
  model artifacts are available.
- `GET /api/readings?city=Delhi&limit=50&offset=0` - paginated observations.
- `GET /api/analytics` - city, year, and AQI bucket aggregates.
- `GET /api/forecasts?city=Delhi` - generated forecasts for all configured
  targets, optionally filtered by city.
- `GET /api/anomalies?city=Delhi` - generated potential anomalies, optionally
  filtered by city.

The API never fabricates forecast or anomaly values. Query parameters are
validated and SQL uses bound parameters for user-provided filters. The summary
endpoint remains usable if optional model artifacts have not yet been created;
the forecast chart then displays its empty state.
