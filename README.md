# Air Quality Intelligence

This project provides an air-quality analytics dashboard, leakage-safe
forecasting, anomaly detection, and an API backed by verified historical data.

## Project status

The data cleaning, MySQL import, analysis, model training, API, and dashboard
phases are implemented locally. Generated datasets and model binaries are
intentionally ignored by Git; they must be produced in each environment.

## Planned workflow

1. Inspect the workspace and dataset.
2. Profile the dataset and approve a data-quality policy.
3. Clean and validate data with complete audit reports.
4. Set up and verify MySQL safely.
5. Import only validated data.
6. Perform analysis and leakage-safe chronological forecasting.
7. Add the API, dashboard, tests, and final documentation.

See [docs/implementation_plan.md](docs/implementation_plan.md) for the
current implementation status and reproducible commands.

## Run the local dashboard

Start the API in one terminal:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\run_backend.py
```

Start the static frontend in a second terminal:

```powershell
.\.venv\Scripts\python.exe scripts\run_frontend.py
```

Open `http://127.0.0.1:5500`. The API documentation is at
`http://127.0.0.1:8000/docs`.

To regenerate the forecast and anomaly artifacts after cleaning the dataset:

```powershell
$env:PYTHONPATH = "src"
.\.venv\Scripts\python.exe scripts\train_models.py
```

The API requires the local MySQL settings in `.env`. Forecast and anomaly
endpoints return the generated artifacts and never fabricate values.
