# Implementation plan

## Phase 0 - Environment and workspace inspection

- **Status:** Complete
- Workspace: `C:\air-quality`
- Existing content: project-local `.venv` only before Phase 1
- Dataset: `bulk_combined_dataset.csv` not found in the workspace
- Git repository: not initialized
- Python: 3.13.5 in `.venv`
- MySQL: `MySQL80` service running and `127.0.0.1:3306` reachable
- No files were changed during inspection

## Phase 1 - Project architecture and folder structure

- **Status:** Complete
- Created the planned source, data, database, documentation, frontend, test,
  artifact, logging, and workflow directories.
- Added safe base configuration files and project documentation.
- Preserved the existing `.venv`.

## Phase 2 - Dataset profiling and data dictionary

- **Status:** Complete; cleaning-policy approval required before Phase 3
- Source supplied: `C:\Users\ASUS\Downloads\bulk_combined_dataset.csv`
- Immutable raw copy: `data/raw/bulk_combined_dataset.csv`
- SHA-256: `ffceb4e2d145054f7d570252d0a277b4525ba31b407e7fefb55567bf2de8875c`
- Observed format: UTF-8 with BOM, comma-delimited, 382,343 rows, 18 columns
- Full-row duplicates beyond the first: 0
- Rows with field-count mismatch: 0
- Important observations: `Datetime` has 2,402 nulls, `Date` has 379,941
  nulls, and `Station` has 338,603 nulls. These fields require semantic review
  before choosing the time/location key.
- Provenance and license: not verified from supplied CSV metadata
- Reports: `data/reports/profile_report.json`,
  `data/reports/profile_report.md`, `docs/data_dictionary.md`, and
  `docs/data_quality_policy.md`

## Phase 3 - Cleaning policy and reproducible pipeline

- **Status:** Complete; database approval gate remains
- Added `src/air_quality/data/cleaning.py`,
  `scripts/clean_dataset.py`, and `scripts/validate_dataset.py`.
- Added focused tests in `tests/unit/test_cleaning.py`.
- Clean output: `data/processed/bulk_combined_dataset_clean.csv`
- Rejected output: `data/rejected/bulk_combined_dataset_rejected.csv`
- Audit reports: `data/reports/cleaning_report.json` and
  `data/reports/cleaning_report.md`
- Result: 382,343 rows read, 382,343 clean, 0 rejected, 0 duplicate rows
  removed, 0 numeric failures, 0 date failures, and 0 field-count failures.
- Clean output SHA-256:
  `21f3c0cc0ab6eb623b4dc693f5a0ac6a7a00063f7447cd9e35b769fe13dd1a09`
- Idempotency check passed: two consecutive runs produced the same clean-file
  checksum.
- Validation script passed with 382,343 rows and 18 standardized columns.

## Later phases

## Phase 4 - MySQL setup and database design

- **Status:** Tooling ready; blocked on local database credentials and inventory
- MySQL80 is running and `127.0.0.1:3306` is reachable.
- Proposed database: `air_quality_db`
- Proposed schema: `database/schema/001_initial_schema.sql`
- Design documentation: `docs/database_design.md`
- No database/table creation or destructive SQL was executed.
- Added safe connection helpers and scripts:
  `src/air_quality/db/connection.py`, `scripts/check_database.py`,
  `scripts/create_database.py`, and `scripts/init_database.py`.
- Installed project-v-env dependencies: SQLAlchemy, PyMySQL, and
  python-dotenv.
- Created `air_quality_db` with `CREATE DATABASE IF NOT EXISTS`.
- Applied five non-destructive schema statements.
- Imported the validated clean CSV using a repeat-safe checksum-tracked batch.
- Import result: 382,343 attempted and inserted rows, 0 rejected.
- Added `scripts/import_clean_data.py` and `scripts/verify_database.py`.
- Database verification passed: 382,343 readings, one completed import batch,
  five cities, and observed timestamps from 2015-01-01 through 2024-12-31.

## Phase 6 - Exploratory data analysis

- **Status:** Complete; model training intentionally not started
- Added read-only database analysis in `src/air_quality/analytics/eda.py` and
  `scripts/run_eda.py`.
- Reports: `data/reports/eda_report.json` and
  `data/reports/eda_report.md`.
- EDA analyzed 382,343 verified database rows across five cities and the
  observed range 2015-01-01 through 2024-12-31.
- The EDA includes city counts/AQI summaries, AQI bucket distribution, null
  counts, yearly AQI summaries, and pollutant min/mean/max statistics.
- No model target, feature dataset, train/test split, or model artifact was
  created.

## Frontend dashboard shell

- **Status:** Complete; waiting for backend API
- Added a responsive dashboard inspired by the supplied screenshot:
  `frontend/index.html`, `frontend/assets/css/styles.css`,
  `frontend/assets/js/api.js`, `frontend/assets/js/charts.js`, and
  `frontend/assets/js/dashboard.js`.
- The UI includes AQI overview, forecast chart, pollutant breakdown,
  historical trends, potential anomalies, health advisory, city filter, and
  report links.
- It intentionally shows empty/loading states instead of fabricated values.
- Model training was not performed and no model files were created.

## Backend API

- **Status:** Complete; forecast/anomaly results intentionally empty
- Added FastAPI app and response schemas in
  `src/air_quality/api/main.py` and `src/air_quality/api/schemas.py`.
- Added `scripts/run_backend.py` for port 8000 and
  `scripts/run_frontend.py` for port 5500.
- Implemented and smoke-tested `/health`, `/api/summary`,
  `/api/readings`, `/api/analytics`, `/api/forecasts`, and
  `/api/anomalies`.
- Verified `/health` database connection, 382,343 reading total, five-city
  analytics, and city filtering for Delhi.
- Frontend server returned HTTP 200 on port 5500 and browser verification
  confirmed live API data, the city filter, charts, and honest empty forecast
  and anomaly states.

Cleaning, validation, MySQL setup/import, analysis, forecasting, API,
dashboard, testing, and final documentation remain gated behind the earlier
phases and explicit approval.
