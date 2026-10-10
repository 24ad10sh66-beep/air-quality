# Air Quality Intelligence

This project will implement an AI-driven air-quality forecasting, pollution
analytics, and environmental decision-support framework.

## Project status

The workspace is currently in **Phase 1: architecture and folder structure**.
The dataset has not yet been added or profiled. Implementation must proceed
phase by phase after review and approval.

## Planned workflow

1. Inspect the workspace and dataset.
2. Profile the dataset and approve a data-quality policy.
3. Clean and validate data with complete audit reports.
4. Set up and verify MySQL safely.
5. Import only validated data.
6. Perform analysis and leakage-safe chronological forecasting.
7. Add the API, dashboard, tests, and final documentation.

See [docs/implementation_plan.md](docs/implementation_plan.md) for the
phase gates and current status.

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

Forecast and anomaly sections intentionally remain empty until their approved
analysis/model phases are completed.
