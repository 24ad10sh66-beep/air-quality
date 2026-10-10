# API

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
  values, data range, and recent AQI trend.
- `GET /api/readings?city=Delhi&limit=50&offset=0` - paginated observations.
- `GET /api/analytics` - city, year, and AQI bucket aggregates.
- `GET /api/forecasts` - currently returns an empty result because models have
  not been trained.
- `GET /api/anomalies` - currently returns an empty result because anomaly
  analysis has not been run.

The API never fabricates forecast or anomaly values. Query parameters are
validated and SQL uses bound parameters for user-provided filters.
